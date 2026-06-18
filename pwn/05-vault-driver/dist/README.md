# Challenge 05: Vault Driver

## Description 

A security vault driver protects access to sensitive resources. Can you bypass its defenses?

## Connectivity

```bash
./run.sh
```

## Files

- `bzImage`: Linux kernel image (v6.18+)
- `rootfs.cpio.gz`: compressed root filesystem (contains `vault_sec.ko` and `init`)
- `run.sh`: QEMU launcher

## Local Testing

Ensure you have `qemu-system-x86_64` installed. 
Run `./run.sh` to boot the environment.
