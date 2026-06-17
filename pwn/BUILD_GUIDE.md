# Build Guide - Production Ready

## What Was Fixed

1. ✅ **Challenge 01 (Entry Gate)**: Fixed Thumb mode interworking and FPU flags.
2. ✅ **Challenge 02 (Token Terminal)**: Resolved 16-bit truncation logic and stack stability.
3. ✅ **Challenge 03 (Staff Chat)**: Stabilized heap consolidation and libc leak timing.
4. ✅ **Challenge 04 (Power Grid)**: Implemented PIE base calculation and BSS stack pivot.
5. ✅ **Challenge 05 (Vault Driver)**: Created deterministic Double-Fetch race and Cred spray.

## Build Commands

### Install Dependencies
```bash
./setup.sh
```

### Build Each Challenge

```bash
# Challenge 01 - ARM32
make -C challenges/01-entry-gate

# Challenge 02 - x86_32
make -C challenges/02-token-terminal

# Challenge 03 - x86_64
make -C challenges/03-staff-chat

# Challenge 04 - ARM64
make -C challenges/04-power-grid

# Challenge 05 - Kernel
make -C challenges/05-vault-driver rootfs
```

## Challenge 05 Notes

The kernel challenge has a dedicated rootfs builder. If you modify the driver or the exploit, you must repack the filesystem:

```bash
cd challenges/05-vault-driver
make rootfs
```

## Binary Verification

After building, verify your binaries in the `dist/` folders:

- `01-entry-gate/dist/doorbell` (ARM32)
- `02-token-terminal/dist/pos` (x86_32)
- `03-staff-chat/dist/chat` (x86_64)
- `04-power-grid/dist/plc` (ARM64)
- `05-vault-driver/dist/rootfs.cpio.gz` (Kernel)

## Testing Locally

Each challenge directory contains a `run.sh` (or `run-qemu.sh`) in its `dist/` folder.

```bash
# Example: Testing Vault Driver
cd challenges/05-vault-driver/dist
./run.sh
```

## Docker Deployment

To start the full arcade complex including all 5 challenges:

```bash
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f
```
