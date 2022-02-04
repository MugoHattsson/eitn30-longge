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

def wrap_message(msg, header):

    wrapped = b"{header}"

    # 8 bytes   shockburst / our protocol / transport (payload)

def make_zoomer(ip_header):

    id = ip_header.id # package id (2 bytes)
    flags = ip_header.flags #flags (3 bits)
    frag_offset = ip_header.frag # fragment offset (1 byte)
    protocol = ip_header.proto # protocol (1 byte)
    dest_ip = ip_header.dst # (4 bytes)




def prepare_packet(packet):
    fragments = []
    if len(packet) not in range(1, 33):
        return

        # start = 5
        # end = 5
        # eth_fmt = f"{start}s{len(packet) - start - end}s{end}"
        # ip_packet = struct.unpack(eth_fmt, packet)
        # ip_fmt = f"{21}s{len(ip_packet[1])-20}"

        # transport_packet = struct.unpack(ip_fmt, ip_packet[1]) 

        # reconstruct header 

        # f"{1}s{1}s{2}s{2}s{2}s{1}s{1}s{2}s{4}s{4}s{len(ip_header)-20}s"
        # ip_header = ip_packet[0]
        # ip_fields_fmt = f"{1}s{1}s{2}s{2}s{2}s{1}s{1}s{2}s{4}s{4}s{len(ip_header)-20}s"
        # ip_fields = struct.unpack(ip_fields_fmt, ip_header)
        # bytes = b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xffhejhej"

    else:
        zoomer = make_zoomer(header)
        fragments.append(wrap_message(packet, zoomer))
    return fragments

def tx(nrf, channel, address, size, queue):
    nrf.open_tx_pipe(address)  # set address of RX node into a TX pipe
    nrf.listen = False
    nrf.channel = channel

    status = []


    while(1):
        try:
            packet = queue.get(timeout = 5)
        except Empty:
            print("The queue is empty!")
            break
        packets = prepare_packet(packet)

        for pkt in packets:

            wrapped = wrap_message(pkt)

            result = nrf.send(wrapped)

            if not result:
               print("send() failed or timed out")
               status.append(False)
            else:
               print("send() successful")
               status.append(True)
    

    print('{} successfull transmissions, {} failures'.format(sum(status), len(status)-sum(status)))

def rx(nrf, channel, address):
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up
    nrf.channel = channel

    print('Rx NRF24L01+ started w/ power {}, SPI freq: {} hz'.format(nrf.pa_level, nrf.spi_frequency))

    received = []

    start_time = None
    start = time.monotonic()
    while (time.monotonic() - start) < 10:
       if nrf.update() and nrf.pipe is not None:
           if start_time is None:
               start_time = time.monotonic()

           received.append(nrf.any())
           rx = nrf.read()  # also clears nrf.irq_dr status flag
           buffer = struct.unpack(f"{len(rx)}s", rx)  # [:4] truncates padded 0s
           # print the only item in the resulting tuple from
           print("Received: {}".format(buffer[0].decode('latin1')))
           #start = time.monotonic()

    print('{} received, {} average'.format(len(received), np.mean(received)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NRF24L01+ test')
    parser.add_argument('--src', dest='src', type=str, default='me', help='NRF24L01+\'s source address')
    parser.add_argument('--dst', dest='dst', type=str, default='me', help='NRF24L01+\'s destination address')
    parser.add_argument('--count', dest='cnt', type=int, default=10, help='Number of transmissions')
    parser.add_argument('--size', dest='size', type=int, default=32, help='Packet size')
    parser.add_argument('--txchannel', dest='txchannel', type=int, default=76, help='Tx channel', choices=range(0,125))
    parser.add_argument('--rxchannel', dest='rxchannel', type=int, default=76, help='Rx channel', choices=range(0,125))

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

    rx_process = Process(target=rx, kwargs={'nrf':rx_nrf, 'address':bytes(args.src, 'utf-8'), 'channel': args.rxchannel})
    rx_process.start()
    time.sleep(1)

    manager = Manager()
    queue = manager.Queue()
    
    tx_process = Process(target=tx, kwargs={'nrf':tx_nrf, 'address':bytes(args.dst, 'utf-8'), 'channel': args.txchannel, 'size':args.size, 'queue':queue})
    tx_process.start()

    tun = TunTapDevice("tun0")
    tun.addr = '11.11.11.1'
    tun.dstaddr = '11.11.11.2'
    tun.netmask = '255.255.255.0'
    tun.mtu = 200
    tun.up()



    packet = tun.read(tun.mtu)[4:]
    print(f"Packet: {packet}")
    ip_packet = sa.IP(packet)
    if (ip_packet.version == 4 and ip_packet.ihl == 5 and ip_packet.flags != sa.FlagValue(2, names=['', 'DF', 'MF'])):

        queue.put(packet)



    tx_process.join()

    rx_process.join()



    



    nonsense_header = "dettaar20byteskanske"
