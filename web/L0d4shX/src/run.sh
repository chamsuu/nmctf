#!/bin/sh
set -e

echo "[+] Building L0d4shX..."
docker build -t ctf-player .

echo "[+] Starting on port 8000..."
docker run -d --restart unless-stopped -p 8000:8000 ctf-player
