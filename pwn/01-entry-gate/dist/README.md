# Challenge 01: Entry Gate

## Description

The entry system relies on a firmware update service. Management believes it is secure, prove them wrong.

## Local Testing

You can run the challenge locally using the ARM emulator:

```bash
# Start the challenge server
# It will listen on port 1337 by default
qemu-arm ./doorbell
```

In a second terminal, connect to it:
```bash
nc localhost 1337
```

**Note:** If the command fails, ensure you have the emulator installed:
`sudo apt-get install qemu-user-static` (or `qemu-arm`)

## File

- `doorbell`: The binary

## Connectivity

Connect to the remote instance:
```bash
nc entrygate.ctf.vuln3ra.com 1337
```
