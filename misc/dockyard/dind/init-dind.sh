#!/bin/sh
# ============================================================
# Nested Docker-in-Docker Seeding Script
# Created by 4mdj4d for Algerian Devs Developer Challenge
# ============================================================

echo "[DinD-Init] Waiting for internal Docker daemon to start..."

# Wait until local Docker daemon is accepting commands
until docker info >/dev/null 2>&1; do
    sleep 1
done

echo "[DinD-Init] Internal Docker daemon is ONLINE!"
echo "[DinD-Init] Pulling lightweight Alpine image..."

# Pre-pull Alpine so the player can inspect it immediately
docker pull alpine:3.19 >/dev/null 2>&1

# Run the secure-vault container in the background with a clean command
docker run -d \
    --name secure-vault \
    --restart always \
    alpine:3.19 \
    tail -f /dev/null

# Write the secret flag silently inside the container's isolated filesystem (at /run/secrets/audit_token)
sleep 0.5
docker exec secure-vault sh -c "mkdir -p /run/secrets && echo 'nmctf{n3v3r_m0unt_d0ck3r_s0ck}' > /run/secrets/audit_token"

echo "[DinD-Init] Setup complete! Nested container running."
