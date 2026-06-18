#!/bin/bash
# Simple rootfs builder using busybox
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/files/bin"
mkdir -p "$SCRIPT_DIR/files/etc"
mkdir -p "$SCRIPT_DIR/files/lib"
mkdir -p "$SCRIPT_DIR/files/usr"

# Copy busybox (assumes installed on host)
if [ -f /bin/busybox ]; then
    cp /bin/busybox "$SCRIPT_DIR/files/bin/"
    cd "$SCRIPT_DIR/files"
    for cmd in sh cat echo ls mount sleep; do
        ln -sf /bin/busybox bin/$cmd
    done
    cd -
fi

# Copy init script
cp "$SCRIPT_DIR/init" "$SCRIPT_DIR/files/"
chmod +x "$SCRIPT_DIR/files/init"

# Copy kernel module
cp "$SCRIPT_DIR/../dist/vault_sec.ko" "$SCRIPT_DIR/files/"
# (Exploit is NOT pre-loaded for the final release)

# Create flag file - matched to docker-compose.yml
echo "nmctf{v4ult_dr1v3r_k3rn3l_uaf_h34p}" > "$SCRIPT_DIR/files/flag.txt"

# Create cpio archive
cd "$SCRIPT_DIR/files"
find . | cpio -o -H newc | gzip > "$SCRIPT_DIR/../dist/rootfs.cpio.gz"
cd -