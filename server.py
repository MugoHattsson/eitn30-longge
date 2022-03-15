import socket

host = ''        # Symbolic name meaning all available interfaces
rec_port = 12345     # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Allows re-connection to a socket in use
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Socket sends data immidatley
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

s.bind((host, rec_port))
s.listen(1)

conn, addr = s.accept()

print('Connected by', addr)
while True:

    try:
        data = conn.recv(6)

        if not data: break
        
        # Echoes back the conntent of the packet
        conn.sendall(data)

    except socket.error:
        print("Error Occured.")
        break

conn.close()