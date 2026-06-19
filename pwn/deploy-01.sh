#!/bin/bash
# Redeploy Challenge 01 to fix FORTIFY_SOURCE error
# Run this on the REMOTE server (20.153.191.20) or wherever entrygate is hosted

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/01-entry-gate"

echo "[*] Rebuilding doorbell binary (fortify disabled)..."
make clean && make

echo "[*] Rebuilding Docker image..."
docker build -t pixelvault/entry-gate:latest .

echo "[*] Restarting container..."
if [ -f docker-compose.yml ]; then
    docker compose up -d --force-recreate
else
    docker compose -f "$DIR/docker-compose.yml" up -d --force-recreate 01-entry-gate
fi

echo "[+] Done. Verify: python3 exploit/solve.py"
