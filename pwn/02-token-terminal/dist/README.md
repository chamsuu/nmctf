# Challenge 02: Token Terminal

## Description

The Token Terminal manages customer orders and refunds. Can you gain access to the maintenance system?

## Local Testing

Run with the provided 32-bit loader :

```bash
# Start the challenge server (port 1337)
./ld-linux.so.2 --library-path . ./pos
```

In a second terminal, connect to it:
```bash
nc localhost 1337
```

**Note:** Ensure binaries are executable (`chmod +x pos ld-linux.so.2`).

## Files

- `pos`: The binary
- `ld-linux.so.2`: 32-bit dynamic linker (glibc 2.27)
- `libc.so.6`: 32-bit C library (glibc 2.27)

## Connectivity

Connect to the remote instance:
```bash
nc tokenterminal.ctf.vuln3ra.com 1337
```
