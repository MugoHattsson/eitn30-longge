from multiprocessing import Process
from multiprocessing import Manager
from queue import Empty, Queue
from circuitpython_nrf24l01.rf24 import RF24
import board
import busio
import digitalio as dio
import time
import struct
import argparse
from random import randint
import numpy as np
from pytun import TunTapDevice
import scapy.all as sa
from rip import RIP

global isbase 
isbase = 0

SPI0 = {
    'MOSI':10,#dio.DigitalInOut(board.D10),
    'MISO':9,#dio.DigitalInOut(board.D9),
    'clock':11,#dio.DigitalInOut(board.D11),
    'ce_pin':dio.DigitalInOut(board.D17),
    'csn':dio.DigitalInOut(board.D8),
    }
SPI1 = {
    'MOSI':20,#dio.DigitalInOut(board.D10),
    'MISO':19,#dio.DigitalInOut(board.D9),
    'clock':21,#dio.DigitalInOut(board.D11),
    'ce_pin':dio.DigitalInOut(board.D27),
    'csn':dio.DigitalInOut(board.D18),
    }

base_address = '11.11.11.1'
mobile_address = '11.11.11.2'


def ip_to_rip(ip_header):
    rip = RIP()
    rip.id = ip_header.id # package id (2 bytes)
    return rip

def prepare_ip(list):
    header = list[0]

    payload = b""

    for frag in list:
        payload += sa.raw(frag.getlayer(1))
         
    return payload


def prepare_packet(payload, rip_header):
    raw_bytes = sa.raw(payload)
    fragments = []
    header_size = len(rip_header) # Should be 3 bytes
    if len(raw_bytes) not in range(1, 33-header_size):
        fragment_size = 32 - header_size

        print("Payload:")
        # payload.show()
        step = 0
        while step < len(payload):
            fragments.append(raw_bytes[step:step+fragment_size])
            step += fragment_size   

        # print("Fragments:")
        # print(fragments)

    # Slap RIP header onto every fragment
    if fragments:
        for offset, fragment in enumerate(fragments):
            rip_header.mf = 0 if offset + 1 == len(fragments) else 1
            rip_header.frag = offset 
            fragments[offset] = sa.raw(rip_header) + fragment

        return fragments
    else:
        return [sa.raw(rip_header) + raw_bytes]

       


def tx(nrf, channel, address, size, queue):
    nrf.open_tx_pipe(address)  # set address of RX node into a TX pipe
    nrf.listen = False
    nrf.channel = channel

    status = []

    print('Tx NRF24L01+ started w/ power {}, SPI freq: {} hz, on channel: {}'.format(nrf.pa_level, nrf.spi_frequency, nrf.channel))

    while(1):
        try:
            packet = queue.get(timeout = 1000)
        except Empty:
            print("The queue is empty!")
            break

        # Create RIP header from IP header
        rip_header = ip_to_rip(packet)
        # rip_header.show()
        
        # Separate IP header from its Data
        # Prepare packet data by possibly fragmenting it
        fragments = prepare_packet(packet, rip_header)


        # Send fragments
        for frag in fragments:
            result = nrf.send(frag)

            if not result:
               print("send() failed or timed out")
               status.append(False)
            else:
               print("send() successful")
               status.append(True)
    

    print('{} successfull transmissions, {} failures'.format(sum(status), len(status)-sum(status)))

def add_fragment(frag, list):
    
    length = len(list)
    
    if length == frag.frag:
       list.append(frag)

    elif length > frag.frag:
        list[frag.frag] = frag     
    else:
        for i in range[frag.frag - length]:
            list.append(None)
        list.append(frag)
    return list

def rx(nrf, channel, address, tun):

    fragments = {}

    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up
    nrf.channel = channel

    print('Rx NRF24L01+ started w/ power {}, SPI freq: {} hz, on channel: {}'.format(nrf.pa_level, nrf.spi_frequency, nrf.channel))

    received = []

    start_time = None
    start = time.monotonic()
    while (time.monotonic() - start) < 1000:
        if nrf.update() and nrf.pipe is not None:
            if start_time is None:
                start_time = time.monotonic()

            received.append(nrf.any())
            rx = nrf.read()  # also clears nrf.irq_dr status flag

            rip = RIP(rx)    
            # rip.show()

            if rip.id in fragments.keys():
                fragments.update({rip.id : add_fragment(rip, fragments[rip.id])})

            else:
                fragments.update({rip.id : [rip]})

            complete = True
            if (fragments[rip.id][-1].mf == 0):
                for item in fragments[rip.id]:
                    if item == None:
                       complete = False
            else:
                complete = False

            
            if complete:
                frags = fragments.pop(rip.id)
                for f in frags:
                    print(f)
                packet = prepare_ip(frags)
                print("Received packet on NRF:")
                print(packet)
                if len(packet) > 20:
                    # sa.IP(packet).show()
                    tun.write(b'\x00\x00\x08\x00' + packet)
                else:
                    print("Packet was None")

    print('{} received, {} average'.format(len(received), np.mean(received)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NRF24L01+ test')
    parser.add_argument('--src', dest='src', type=str, default='me', help='NRF24L01+\'s source address')
    parser.add_argument('--dst', dest='dst', type=str, default='me', help='NRF24L01+\'s destination address')
    parser.add_argument('--count', dest='cnt', type=int, default=10, help='Number of transmissions')
    parser.add_argument('--size', dest='size', type=int, default=32, help='Packet size')
    parser.add_argument('--txchannel', dest='txchannel', type=int, default=76, help='Tx channel', choices=range(0,125))
    parser.add_argument('--rxchannel', dest='rxchannel', type=int, default=76, help='Rx channel', choices=range(0,125))
    parser.add_argument('--isbase', dest='isbase', type=int, default=0, help='Whether the unit is mobile or the base station', choices=range(0,2))

    args = parser.parse_args()

    SPI0['spi'] = busio.SPI(**{x: SPI0[x] for x in ['clock', 'MOSI', 'MISO']})
    SPI1['spi'] = busio.SPI(**{x: SPI1[x] for x in ['clock', 'MOSI', 'MISO']})

    # initialize the nRF24L01 on the spi bus object
    rx_nrf = RF24(SPI0['spi'], SPI0['csn'], SPI0['ce_pin'])
    tx_nrf = RF24(SPI1['spi'], SPI1['csn'], SPI1['ce_pin'])

    for nrf in [rx_nrf, tx_nrf]:
        nrf.data_rate = 1
        nrf.auto_ack = True
        #nrf.dynamic_payloads = True
        nrf.payload_length = 32
        nrf.crc = True
        nrf.ack = 1
        nrf.spi_frequency = 20000000

    tun = TunTapDevice("tun0")

    isbase = args.isbase

    rx_process = Process(target=rx, kwargs={'nrf':rx_nrf, 'address':bytes(args.src, 'utf-8'), 'channel': args.rxchannel, 'tun': tun})
    rx_process.start()
    time.sleep(1)

    manager = Manager()
    queue = manager.Queue()
    
    tx_process = Process(target=tx, kwargs={'nrf':tx_nrf, 'address':bytes(args.dst, 'utf-8'), 'channel': args.txchannel, 'size':args.size, 'queue':queue})
    tx_process.start()


    tun.addr = base_address if isbase else mobile_address
    tun.dstaddr = mobile_address if isbase else base_address
    tun.netmask = '255.255.255.0'
    tun.mtu = 30000
    tun.up()

    try:
        while True:
            packet = tun.read(tun.mtu)[4:]
            ip_packet = sa.IP(packet)[0]
            if (ip_packet.version == 4):
                print("Received packet on tun0:")
                # ip_packet.show()
                queue.put(ip_packet)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt!")
        


    print("Joining")

    tx_process.join()
    rx_process.join()

    tun.down()

    print("Graceful shutdown complete")