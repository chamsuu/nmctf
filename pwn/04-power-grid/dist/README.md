# Challenge 04: Power Grid

## Description
The Power Grid Controller is protected by proprietary ARM64 defenses. Can you break in?

## Local Testing

This challenge uses ARM64 architecture and interacts via `stdin/stdout`.

### Option 1: Direct Execution (via QEMU)
You can run it directly in your terminal for debugging:
```bash
# Requires qemu-aarch64 and libc6-arm64-cross
qemu-aarch64 -L /usr/aarch64-linux-gnu ./plc
```

### Option 2: Network Service (for Exploit Scripts)
The remote server wraps this binary in a `socat` listener. To test your exploit script locally against a port:
```bash
# Start a local server on port 1337
socat TCP-LISTEN:1337,reuseaddr,fork EXEC:"qemu-aarch64 -L /usr/aarch64-linux-gnu ./plc"
```

In a second terminal, connect to it:
```bash
nc localhost 1337
```

## Files
- `plc`: The binary

## Connectivity

Connect to the remote instance:
```bash
nc powergrid.ctf.vuln3ra.com 1337
```
