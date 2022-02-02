from multiprocessing import Process
from circuitpython_nrf24l01.rf24 import RF24
import board
import busio
import digitalio as dio
import time
import struct
import argparse
from random import randint
import numpy as np

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

def tx(nrf, channel, address, size, msg):
    nrf.open_tx_pipe(address)  # set address of RX node into a TX pipe
    nrf.listen = False
    nrf.channel = channel

    status = []
    buffer = np.random.bytes(size)

    start = time.monotonic()
    count = 1

    assert(len(msg) <= 32)

    while count:
    # use struct.pack to packetize your data
    # into a usable payload

       buffer = struct.pack(f"{len(msg)}s", msg.encode("latin1"))
       print("Sending: {} as struct: {}".format(msg, buffer))
       result = nrf.send(buffer)
       if not result:
           print("send() failed or timed out")
           status.append(False)
       else:
           print("send() successful")
           status.append(True)
       count -= 1

    print('{} successfull transmissions, {} failures'.format(sum(status), len(status)-sum(status)))

def rx(nrf, channel, address):
    nrf.open_rx_pipe(0, address)
    nrf.listen = True  # put radio into RX mode and power up
    nrf.channel = channel

    print('Rx NRF24L01+ started w/ power {}, SPI freq: {} hz'.format(nrf.pa_level, nrf.spi_frequency))

    received = []

    start_time = None
    start = time.monotonic()
    while (time.monotonic() - start) < 20:
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

    start = time.monotonic()
    while (time.monotonic() - start) < 20:
        msg = input(">")
        if len(msg) not in range(1,33):
            rx_process.kill()
            break

        tx_process = Process(target=tx, kwargs={'nrf':tx_nrf, 'address':bytes(args.dst, 'utf-8'), 'channel': args.txchannel, 'size':args.size, 'msg':msg})
        tx_process.start()
        tx_process.join()

    rx_process.join()
