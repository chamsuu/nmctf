from flag import flag1,flag2
from Crypto.Util.number import long_to_bytes,bytes_to_long,getPrime
from os import urandom
from random import randint
p, q, z = [getPrime(1024 - i) for i in range(3)]
assert p > q > z
e = 0x10001

n1 = p * q
n2 = q * z

c1 = pow(bytes_to_long(flag1), e, n1)
c2 = pow(bytes_to_long(flag2), e, n2)

E = bytes_to_long(urandom(50))
r = randint(0,1000)
d1 = pow(0x10001,-1,(p-1)*(q-1))
d2 = pow(0x10001,-1,(q-1)*(z-1))

assert pow(c1,d1,n1) == bytes_to_long(flag1)
assert pow(c2,d2,n2) == bytes_to_long(flag2)
with open('files/secret.txt','w') as f:
    f.write(f'd1: {d1}\n')
    f.write(f'd2: {d2}\n')

with open('files/output.txt','w') as f :
    f.write(f'n1: {n1}\n')
    f.write(f'c1: {c1}\n')
    f.write(f'c2: {c2}\n')
    f.write(f'eq : {n1*E + n2 + r}')
