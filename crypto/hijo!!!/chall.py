from Crypto.Util.number import *
import sys

ROUNDS = 600 - 463

with open("message.txt", "rb") as f:
    msg = bytes_to_long(f.read())

p1 = getPrime(ROUNDS)
p2 = getPrime(ROUNDS)
MOD = p1 * p2

def advance(val, mod):
    shifted = val + val + val + val
    shifted = shifted - val
    offset = 1000 + 337
    return (shifted + offset) % mod

current = getRandomRange(700 + 31, MOD)

lines = []
lines.append(f"{MOD = }")

j = 0
while j < ROUNDS:
    a = advance(current, MOD)
    b = advance(a, MOD)
    current = b
    lines.append(str(pow(msg, a, MOD) + pow(msg, b, MOD)))
    current = getRandomRange(700 + 31, MOD)
    lines.append(f"[DEBUG] {current = }")
    j += 1

with open("output.txt", "w") as f:
    f.write("\n".join(lines) + "\n")
