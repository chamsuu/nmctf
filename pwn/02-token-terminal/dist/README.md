# Token Terminal

**Category:** PWN  
**Difficulty:** Medium  
**Points:** 400  
**Author:** N4dj1b

## Description

Welcome to the Token Terminal System! This point-of-sale terminal processes customer orders and manages refund requests. As a security researcher, your task is to find and exploit vulnerabilities in the order processing system.

The terminal accepts token-based operations including order processing, record management, and refund handling. Your objective is to exploit the system to gain unauthorized access to the maintenance function.

## Challenge Details

- **Architecture:** x86 (32-bit)
- **Binary:** `pos` - Stripped 32-bit ELF executable
- **Connection:** `nc <host> <port>` or use the provided exploit

## Files

- `pos` - Stripped 32-bit binary
- `docker-compose.yml` - Docker deployment configuration
- `Dockerfile` - Container build instructions

## Local Testing

### Docker (Recommended)
```bash
docker-compose up -d
python3 exploit/solve.py --docker
docker-compose down
```

### Native Build
```bash
make
./pos
python3 exploit/solve.py --host localhost --port 1337
```

Requires:
```bash
gcc-multilib  # For building 32-bit binaries
python3-pwntools  # For the exploit
```

## Exploit Usage

The exploit supports multiple modes:

```bash
# Docker deployment (addresses hardcoded)
python3 exploit/solve.py --docker

# Local testing (extracts symbols from binary)
python3 exploit/solve.py --host localhost --port 1337

# Remote CTF (manual address override)
python3 exploit/solve.py --host ctf.example.com --port 13372 \
    --override-template 0x0804b088 \
    --override-sysmaint 0x0804880f

# Use custom binary for symbol extraction
python3 exploit/solve.py --host ctf.example.com --port 13372 \
    --binary /path/to/challenge_binary
```

## Remote Play

For the actual CTF deployment:
```bash
nc <host> <port>
# Or use the exploit script
python3 exploit/solve.py --host <host> --port <port> --docker
```

## Environment

- **Base Image:** Ubuntu 18.04
- **glibc Version:** 2.27-3ubuntu1.6
- **Compiler:** gcc 7.5.0
- **Compilation:** `-m32 -O1 -fno-pie -no-pie -fno-stack-protector`

## Security Properties

- **NX:** Enabled
- **RELRO:** Partial
- **Stack Canary:** Disabled
- **PIE:** Disabled (No PIE)

## Hints

1. Analyze the integer overflow in the quantity calculation
2. Understand the heap layout and tcache behavior
3. Examine the refund mechanism for logic bugs
4. Look for function pointers in global state
