#!/usr/bin/env bash
set -e
docker build -t pixelvault-staff-chat . -q
docker run --rm -p 1337:1337 pixelvault-staff-chat
echo "[*] Challenge running at localhost:1337"