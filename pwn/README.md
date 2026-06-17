# NumidianCTF 2026 - PWN Challenges

BuildingOS v3.1 · Smart Arcade Complex · 5 Challenges

## Challenges

| # | Name | Difficulty | Architecture | Port | Technique |
|---|------|------------|--------------|------|-----------|
| 01 | Entry Gate | Easy | ARM32 | 13371 | ARM32 ROP + Thumb |
| 02 | Token Terminal | Medium | x86_32 | 13372 | Integer Overflow + House of Spirit |
| 03 | Staff Chat | Medium | x86_64 | 13373 | UAF + XOR Encryption + Tcache |
| 04 | Power Grid | Hard | ARM64 | 13374 | PIE + Custom Canary + Stack Pivot |
| 05 | Vault Driver | Hard | Kernel x86_64 | 13375 | TOCTOU Race + Cred Overwrite |

## Quick Start

```bash
# Build all challenges
./setup.sh
make -C challenges/01-entry-gate
make -C challenges/02-token-terminal
make -C challenges/03-staff-chat
make -C challenges/04-power-grid
make -C challenges/05-vault-driver

# Start all challenges
docker-compose up -d

# Test individual challenge (e.g. 05)
cd challenges/05-vault-driver/dist
./run.sh
```

## Tool Requirements

- ARM32/64: `arm-linux-gnueabihf-gcc`, `aarch64-linux-gnu-gcc`
- x86_32: `gcc-multilib`
- Utilities: `qemu-user-static`, `qemu-system-x86`, `socat`, `cpio`

## Challenge 05 Notes

The kernel challenge requires `dist/bzImage` and a generated `dist/rootfs.cpio.gz`. 
Build the rootfs with:
```bash
cd challenges/05-vault-driver
make rootfs
```

## Health Check

```bash
for PORT in 13371 13372 13373 13374 13375; do
    nc -z localhost $PORT && echo "OK: $PORT" || echo "FAIL: $PORT"
done
```