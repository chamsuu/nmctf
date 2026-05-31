#!/bin/bash
# ============================================================
#  CTFd-Whale Umbrella Bootstrap & Routing Script
# ============================================================

# 1. Start the parent Docker-in-Docker daemon in the background
echo "[Umbrella] Starting internal Docker-in-Docker daemon..."
dockerd --host=unix:///var/run/docker.sock &

# Wait for parent dockerd daemon to be fully ready
until docker info >/dev/null 2>&1; do
    echo "[Umbrella] Waiting for parent Docker daemon..."
    sleep 1
done

echo "[Umbrella] Parent Docker daemon is ONLINE!"

# 2. Boot up the inner challenge compose network
echo "[Umbrella] Starting inner challenge containers via Docker Compose..."
docker-compose -f /challenge/docker-compose.yml up -d --build

# 3. Static Flag Seeding
# The static flag 'nmctf{n3v3r_m0unt_d0ck3r_s0ck}' is automatically seeded 
# inside the nested vault container by the inner 'dind' container during startup.

# 4. Route incoming SSH connections to the nested jumpbox container
echo "[Umbrella] Port forwarding container port 22 to inner jumpbox (localhost:2222)..."
exec socat TCP-LISTEN:22,fork,reuseaddr TCP:127.0.0.1:2222
