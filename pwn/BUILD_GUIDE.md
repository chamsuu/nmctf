# Build Guide - Fixed Issues

## What Was Fixed

1. ✅ **Challenge 01 (ARM32)**: Added FPU flags to compiler
2. ✅ **Challenge 02 (x86_32)**: Fixed string length warning and House of Spirit implementation
3. ✅ **Challenge 05 (Kernel)**: Fixed rootfs build script paths
4. ✅ **Setup script**: Updated package names for newer systems

## Build Commands

### Install Dependencies
```bash
cd /home/n4dj1b/ctf/numidian26k/test_pwn/challs
./setup.sh
```

### Build Each Challenge

```bash
# Challenge 01 - ARM32 (fixed)
cd challenges/01-entry-gate && make

# Challenge 02 - x86_32 (fixed)
cd challenges/02-token-terminal && make

# Challenge 03 - x86_64 (already built)
cd challenges/03-staff-chat && make clean && make

# Challenge 04 - ARM64 (already built)
cd challenges/04-power-grid && make clean && make

# Challenge 05 - Kernel (simplified)
cd challenges/05-vault-driver && make
```

## Challenge 05 Special Instructions

The kernel challenge requires additional setup:

```bash
# Install busybox if not present
sudo apt-get install busybox

# Build rootfs only (this will work now)
cd challenges/05-vault-driver && make

# For kernel module compilation (advanced):
# You need Linux 5.15 kernel headers installed
sudo apt-get install linux-headers-5.15.0-generic
cd challenges/05-vault-driver/kernel
make -C /lib/modules/5.15.0/build M=$(pwd) modules
```

## Expected Results

After building, you should have:

- `challenges/01-entry-gate/dist/doorbell` ✅
- `challenges/02-token-terminal/dist/pos` ✅  
- `challenges/03-staff-chat/dist/chat` ✅
- `challenges/04-power-grid/dist/plc` ✅
- `challenges/05-vault-driver/dist/rootfs.cpio.gz` ✅

## Testing Challenges

### Test Challenge 03 (x86_64)
```bash
cd challenges/03-staff-chat
./dist/chat
# Test the menu functionality
```

### Test Challenge 04 (ARM64)
```bash
cd challenges/04-power-grid
qemu-aarch64 ./dist/plc
# Test the packet handling
```

## Next Steps

1. Build all challenges using the commands above
2. Test each challenge locally
3. Set up Docker containers for deployment
4. Create distribution packages for players

## Docker Deployment

```bash
# Build Docker images
cd challenges/01-entry-gate && docker build -t pixelvault-entry-gate .
cd challenges/02-token-terminal && docker build -t pixelvault-token-terminal .
cd challenges/03-staff-chat && docker build -t pixelvault-staff-chat .
cd challenges/04-power-grid && docker build -t pixelvault-power-grid .
# Challenge 05 requires manual kernel setup

# Start all services
cd /home/n4dj1b/ctf/numidian26k/test_pwn/challs
docker-compose up -d
```
