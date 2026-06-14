# Entry Gate Firmware
**Category:** PWN  
**Difficulty:** Easy  
**Points:** 100  
**Author:** N4dj1b

## Description

Welcome to the PixelVault Entry System! As a security engineer, you need to test the firmware update mechanism for vulnerabilities.

The firmware update service accepts binary payloads for processing. Your task is to find and exploit a vulnerability in the update handler.

## Challenge Details

- **Architecture:** ARM32 (ARMv7-A)
- **Binary:** Static linked ARM32 executable
- **Connection:** `nc <host> <port>`

## Files

- `doorbell` - Stripped ARM32 binary
- `run-qemu.sh` - QEMU-based local testing

## Local Testing

### QEMU
```bash
./run-qemu.sh
# Challenge available at: nc localhost 1337
# Press Ctrl+C to stop
```

Requires QEMU ARM emulation:
```bash
sudo apt-get install qemu-user-static  # or qemu-arm
```

## Remote Play

For the actual CTF, connect to the deployed instance:
```bash
nc <host> <port>
```
