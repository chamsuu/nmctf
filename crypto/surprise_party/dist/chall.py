#!/usr/bin/env python3
"""Secret chat utility — encrypts messages for secure sharing."""
import os
import random


class SecretChat:
    def __init__(self, key):
        self.key = key

    def encrypt(self, data):
        random.seed(self.key)
        return bytes([b ^ random.randint(0, 255) for b in data])


def main():
    key = int.from_bytes(os.urandom(4), "big")

    msg1 = open("msg1.txt", "rb").read()
    msg2 = open("msg2.txt", "rb").read()

    ct1 = SecretChat(key).encrypt(msg1)
    ct2 = SecretChat(key).encrypt(msg2)

    print(f"ct1 = {ct1.hex()}")
    print(f"ct2 = {ct2.hex()}")


if __name__ == "__main__":
    main()
