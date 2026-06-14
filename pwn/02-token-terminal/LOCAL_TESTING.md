# Local Testing Guide

## Quick Start

### Option 1: Using Docker (Recommended for CTF Environment)
```bash
cd challenges/02-token-terminal
docker compose up -d
python3 exploit/solve.py --docker
docker compose down
```

**Important:** Use the `--docker` flag when running against the Docker container. The Docker binary has different memory addresses than the local build.

### Option 2: Local Testing (For development)
```bash
cd challenges/02-token-terminal
make
./pos
# In another terminal:
python3 exploit/solve.py --host localhost --port 1337
```

### Option 3: Remote CTF Server
```bash
# If you know the addresses (from analysis):
python3 exploit/solve.py --host ctf.example.com --port 13372 \
    --override-template 0x0804b088 \
    --override-sysmaint 0x0804880f

# Or try Docker addresses first (if it matches the CTF environment):
python3 exploit/solve.py --host ctf.example.com --port 13372 --docker

# Or use your local binary for symbol extraction:
python3 exploit/solve.py --host ctf.example.com --port 13372 \
    --binary /path/to/ctf/binary
```

## Exploit Address Options

The exploit supports multiple ways to specify memory addresses:

### 1. **--docker** (Easiest for Docker/local deployment)
Uses hardcoded addresses for the Docker container:
```bash
python3 exploit/solve.py --docker
```

### 2. **Binary symbols** (Default for local testing)
Extracts symbols from a local binary:
```bash
python3 exploit/solve.py --binary ../build/pos
```

### 3. **Manual override** (For remote/unknown environments)
Specify addresses manually:
```bash
python3 exploit/solve.py \
    --override-template 0x0804b088 \
    --override-sysmaint 0x0804880f
```

### Priority Order
1. Manual overrides (`--override-*`) - highest priority
2. Docker flag (`--docker`)
3. Binary symbols (default)

## Environment Requirements

### Tested and Working Environments:
- ✅ **Ubuntu 18.04 (Docker)** with glibc 2.27
- ✅ **Debian/Kali** with glibc 2.42
- ✅ **Any glibc version 2.27+** (BSS region check provides compatibility)

### Development Environment Setup

If you want to build and test natively:

#### 1. Install Required Packages
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y gcc-multilib python3-pwnc

# Kali/Debian
sudo apt-get update
sudo apt-get install -y gcc-multilib python3-pwnc
```

#### 2. Build the Challenge
```bash
cd challenges/02-token-terminal/src
gcc -m32 -O1 -fno-stack-protector -no-pie -o pos pos.c
cp pos ../build/
cp pos ../
```

#### 3. Create Flag File
```bash
echo "CTF{test_flag}" > challenges/02-token-terminal/flag.txt
```

#### 4. Run the Server
```bash
cd challenges/02-token-terminal
./pos
```

#### 5. Run the Exploit (in another terminal)
```bash
cd challenges/02-token-terminal
python3 exploit/solve.py --host localhost --port 1337
```

**Note:** Do NOT use the `--docker` flag for local testing. Only use `--docker` when running against the Docker container.

## Troubleshooting

### Issue: "Connection refused"
**Solution:** Make sure the server is running on port 1337

### Issue: Exploit fails at different steps
**Solution:** Check your glibc version:
```bash
ldd --version
```

If your glibc version is very old (< 2.27), the challenge may not work due to allocator differences.

### Issue: Python import errors
**Solution:** Install pwntools:
```bash
pip3 install pwntools
```

### Issue: KeyError: 'g_state' when using stripped binary
**Solution:** Use `--docker` flag or manual overrides:
```bash
# Option 1: Use Docker addresses
python3 exploit/solve.py --docker

# Option 2: Manual address override
python3 exploit/solve.py --override-template 0x0804b088 --override-sysmaint 0x0804880f
```

## Docker Environment Details

The Docker container uses:
- **Base Image**: Ubuntu 18.04
- **glibc Version**: 2.27-3ubuntu1.6
- **gcc Version**: (Ubuntu 18.04 default)
- **Compilation**: `-m32 -O1 -fno-stack-protector -no-pie`

This is the intended CTF target environment.

## Verification

To verify your local setup:

```bash
# Check glibc version
ldd --version

# Check ASLR
cat /proc/sys/kernel/randomize_va_space
# Should be 0, 1, or 2 (all should work with BSS region check)

# Verify binary
file pos
# Should show: ELF 32-bit LSB executable, Intel 80386

# Test connection
echo "6" | nc localhost 1337
# Should show the banner and exit cleanly
```

## Common Issues Fixed

### glibc Version Differences
**Problem:** Exploit worked with glibc 2.42 but failed with glibc 2.27
**Solution:** Changed delete operation to use BSS region check instead of exact pointer equality, making it compatible across glibc versions

### ASLR Issues
**Problem:** ASLR randomizing addresses
**Solution:** Challenge uses -no-pie (PIE disabled) and BSS region check instead of hardcoded addresses, making it ASLR-resistant

### Compiler Optimization
**Problem:** g_pholder being optimized away
**Solution:** Made g_pholder volatile and added BSS region check to reduce optimization sensitivity
