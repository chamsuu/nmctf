#!/bin/bash

if ! command -v qemu-aarch64 &> /dev/null; then
    echo "Error: qemu-aarch64 not found. Install it with: sudo apt install qemu-user-static"
    exit 1
fi

LIB_PATH="/usr/aarch64-linux-gnu"
if [ ! -d "$LIB_PATH" ]; then
    echo "Error: $LIB_PATH not found. Install it with: sudo apt install libc6-arm64-cross"
    exit 1
fi

echo "[*] Starting Power Grid PLC locally..."
qemu-aarch64 -L "$LIB_PATH" ./plc