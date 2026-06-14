#!/usr/bin/env bash
# Alternative: Run with QEMU user-mode emulation

# Try qemu-arm-static first, fallback to qemu-arm
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

echo "[*] Starting challenge with QEMU ARM emulation..."
echo "[*] Using: $QEMU_BIN"
echo "[*] Challenge will listen on port 1337"
echo "[*] Test with: nc localhost 1337"
echo "[*] Press Ctrl+C to stop"
$QEMU_BIN ./doorbell
