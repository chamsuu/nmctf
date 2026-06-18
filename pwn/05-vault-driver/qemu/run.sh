#!/usr/bin/env bash
# QEMU launcher for kernel challenge
# NOTE: Requires pre-built kernel image at dist/bzImage

exec timeout 600 qemu-system-x86_64 \
    -kernel   /challenge/dist/bzImage \
    -initrd   /challenge/dist/rootfs.cpio.gz \
    -append   "console=ttyS0 quiet kaslr" \
    -cpu      kvm64,+smep,+smap \
    -m        512M \
    -nographic \
    -monitor  /dev/null \
    -no-reboot