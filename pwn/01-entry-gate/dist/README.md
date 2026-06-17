# Challenge 01: Entry Gate
**Category:** PWN  
**Difficulty:** Easy  
**Points:** 100  
**Author:** N4dj1b

## Description

The entry system relies on a firmware update service. Management believes it is secure, prove them wrong.

## Files

- `doorbell`: binary
- `run-qemu.sh`: QEMU-based local testing

## Local Testing

```bash
./run-qemu.sh
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
