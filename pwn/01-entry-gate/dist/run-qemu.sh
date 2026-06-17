#!/usr/bin/env bash
PORT=1337

QEMU_BIN=""
if command -v qemu-arm-static &> /dev/null; then
    QEMU_BIN="qemu-arm-static"
elif command -v qemu-arm &> /dev/null; then
    QEMU_BIN="qemu-arm"
else
    echo "[!] qemu-arm not found"
    echo "[!] Install with: sudo apt-get install qemu-user-static"
    exit 1
fi

if ! command -v socat &> /dev/null; then
    echo "[!] socat not found"
    echo "[!] Install with: sudo apt-get install socat"
    exit 1
fi

socat TCP-LISTEN:$PORT,reuseaddr,fork EXEC:"$QEMU_BIN ./doorbell"