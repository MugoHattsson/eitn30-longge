import socket
import time
import threading
import sys
import math

host = '11.11.11.1'
port = 12345 # The same port as used by the server

nbrReplies = 0
avgLatency = 0
delay = 0
run = True

def timeMillis():
    return int(time.time() * 1000)

def reader():
    global nbrReplies
    global avgLatency
    global run

    while run:
        data = s.recv(1024)  
        replyTime = int.from_bytes(data, 'big')
        t = timeMillis()
        latency = t - replyTime
        
        # Check for unreasonably high latency, packet corrupted
        if abs(latency) > 100000:
            continue

        # Iteratively recomputes the mean
        nbrReplies += 1
        avgLatency = avgLatency + 1/nbrReplies*(latency - avgLatency)
        print('Received packet with latency:', latency, 'ms, avg:', avgLatency, 'nbr of recived packages:', nbrReplies)

    print("Read thread done") 


def writer():
    global delay
    global run

    while run:
        payload = bytearray(100)
        timeStamp = timeMillis().to_bytes(6, 'big')
        payload[0:5] = timeStamp
        s.sendall(timeStamp)
        time.sleep(delay)

    print("Write thread done")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Requires data rate arugment (nbr of bytes/sec)")
        exit()

    dataRate = int(sys.argv[1])

    if(dataRate < 100):
        print("To low data rate, requires at least 100 bytes/sec")
        exit()

    nPackets = math.floor(dataRate / 100)
    delay = 1/nPackets

    print("Connecting to server")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect((host, port))

    print("Starting measurement")
    t1 = threading.Thread(target=reader)
    t2 = threading.Thread(target=writer)
    t1.start()
    t2.start()

    # Sleeps for 1 minute
    time.sleep(60)
    run = False

    t2.join()
    s.close()

    print("=========================")
    print("Data rate:", dataRate, "Avg latency:", avgLatency, "Nbr sent packages", nbrReplies)