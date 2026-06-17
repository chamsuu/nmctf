#!/usr/bin/env python3
import os
import random

class SecretChat:
    def __init__(self, key):
        self.key = key

    def encrypt(self, data):
        random.seed(self.key)
        return bytes([b ^ random.randint(0, 255) for b in data])


def main():
    key = int.from_bytes(os.urandom(6), "big")

    with open("src/msgs.txt", "rb") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    cipher = SecretChat(key)

    with open("output.txt", "w") as out:
        for i, line in enumerate(lines):
            print(line)
            ct = cipher.encrypt(line)
            out.write(f"msg{i} = {ct.hex()}\n")


if __name__ == "__main__":
    main()

