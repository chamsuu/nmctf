#!/usr/bin/env python3
import os
from Crypto.Util.number import getPrime, bytes_to_long

flag = os.environ.get("FLAG", "nmCTF{test_flag}")

p = getPrime(512)
q = getPrime(512)
n = p * q
phi = (p - 1) * (q - 1)
e = phi - 1

m = bytes_to_long(flag.encode())
c = pow(m, e, n)

print(f"n = {n}")
print(f"e = {e}")
print(f"c = {c}")
