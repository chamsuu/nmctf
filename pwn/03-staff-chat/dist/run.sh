#!/usr/bin/env bash
# Run the binary using the provided libc and loader for local-remote parity
chmod +x ./chat ./ld-linux-x86-64.so.2
./ld-linux-x86-64.so.2 --library-path . ./chat