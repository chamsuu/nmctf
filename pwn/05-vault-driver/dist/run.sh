#!/usr/bin/env bash

exec qemu-system-x86_64 \
    -kernel   ./bzImage \
    -initrd   ./rootfs.cpio.gz \
    -append   "console=ttyS0 quiet kaslr panic=1" \
    -cpu      kvm64,+smep,+smap \
    -m        512M \
    -nographic \
    -monitor  /dev/null \
    -no-reboot
