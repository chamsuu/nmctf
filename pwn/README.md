# NumidianCTF 2026 - PWN Challenges

BuildingOS v3.1 · Smart Arcade Complex · 5 Challenges

## Challenges

| # | Name | Difficulty | Architecture | Port | Technique |
|---|------|------------|--------------|------|-----------|
| 01 | Entry Gate Firmware | Easy | ARM32 | 13371 | ARM32 ROP + Thumb |
| 02 | Token Exchange Terminal | Medium | x86_32 | 13372 | Integer Overflow + House of Spirit |
| 03 | Staff Chat Module | Medium | x86_64 | 13373 | UAF + XOR Encryption + Tcache |
| 04 | Arcade Power Grid Controller | Hard | ARM64 | 13374 | Custom Canary + Stack Pivot |
| 05 | Security Vault Driver | Hard | Kernel x86_64 | 13375 | Race Condition + Cred Overwrite |

## Quick Start

```bash
# Build all challenges
cd challenges/01-entry-gate && make
cd ../02-token-terminal && make
cd ../03-staff-chat && make
cd ../04-power-grid && make
cd ../05-vault-driver && make

# Start all challenges
docker-compose up -d

# Test individual challenge
cd challenges/01-entry-gate
./dist/run.sh
```

## Tool Requirements

- ARM32: `arm-linux-gnueabihf-gcc`
- ARM64: `aarch64-linux-gnu-gcc`
- x86_32: `gcc -m32`
- Analysis: `ropper`, `checksec`, `qemu-user-static`

## Challenge 05 Notes

The kernel challenge requires a pre-built Linux 5.15 kernel. Place the kernel image at:
`challenges/05-vault-driver/dist/bzImage`

Build the kernel module:
```bash
cd challenges/05-vault-driver/kernel
make -C /lib/modules/5.15.0/build M=$(pwd) modules
```

## Health Check

```bash
for PORT in 13371 13372 13373 13374 13375; do
    nc -z localhost $PORT && echo "OK: $PORT" || echo "FAIL: $PORT"
done
```