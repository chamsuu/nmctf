# Challenge 03: Staff Chat

## Description

The internal staff chat system recently received a security update designed to protect archived messages. Prove it isn't enough.

## Local Testing

This is a standard x86_64 Linux binary. 

### Option 1: Direct Execution
You can run it directly in your terminal for debugging:
```bash
./ld-linux-x86-64.so.2 --library-path . ./chat
```

### Option 2: Network Service (for Exploit Scripts)
The remote server wraps this binary in a `socat` listener. To test your exploit script locally against a port:
```bash
# Start a local server on port 1337
socat TCP-LISTEN:1337,reuseaddr,fork EXEC:"./ld-linux-x86-64.so.2 --library-path . ./chat"
```

In a second terminal, connect to it:
```bash
nc localhost 1337
```

## Files

- `chat`: The binary
- `libc.so.6`: The provided glibc
- `ld-linux-x86-64.so.2`: The matching dynamic linker

## Connectivity

Connect to the remote instance:
```bash
nc staffchat.ctf.vuln3ra.com 1337
```