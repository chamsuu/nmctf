# Challenge 02: Token Terminal

## Description

The Token Terminal manages customer orders and refunds. Can you gain access to the maintenance system?

## Local Testing

You can run the challenge locally on an x86_64 host (requires 32-bit libs):

```bash
# Start the challenge server
# It will listen on port 1337 by default
./pos
```

In a second terminal, connect to it:
```bash
nc localhost 1337
```

**Note:** Ensure the binary is executable (`chmod +x pos`).

## Files

- `pos`: The binary

## Connectivity

Connect to the remote instance:
```bash
nc tokenterminal.ctf.vuln3ra.com 1337
```
