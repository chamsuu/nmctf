#!/bin/bash
# Setup script for NumidianCTF 2026 PWN challenges

echo "[*] Installing dependencies..."

# Install basic tools
sudo apt-get update
sudo apt-get install -y \
    gcc \
    gcc-multilib \
    g++-multilib \
    qemu-user-static \
    socat \
    ropper \
    checksec \
    python3-pwntools

# Install the missing 32-bit library
sudo apt-get install libc6-i386 lib32gcc-s1

# Install ARM cross-compilers
sudo apt-get install -y \
    gcc-arm-linux-gnueabihf \
    g++-arm-linux-gnueabihf \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu

echo "[+] Setup complete!"
echo ""
echo "[*] To build challenges:"
echo "  cd challenges/01-entry-gate && make"
echo "  cd challenges/02-token-terminal && make  # May need 32-bit libraries"
echo "  cd challenges/03-staff-chat && make"
echo "  cd challenges/04-power-grid && make"
echo "  cd challenges/05-vault-driver && make"
echo ""
echo "[*] Note: Challenge 02 requires 32-bit libraries. On 64-bit systems:"
echo "  sudo apt-get install libc6-i386 lib32gcc-s1"
