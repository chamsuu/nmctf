# 🐳 DOCKYARD — CTF Challenge

## Category: Misc / DevSecOps | Difficulty: Medium-Hard | Points: 450
**Author:** 4mdj4d (Algerian Devs)

An interactive, multi-container lateral movement and container escape challenge. Players start on a low-privilege jumpbox, discover leaked Jenkins credentials, build a pipeline script to gain execution, and abuse a mounted Docker socket inside the pipeline runner via raw HTTP API queries to extract a secret flag from a highly isolated database.

### Host Security (Docker-in-Docker Sandbox)
Unlike standard socket exploitation challenges that mount the host's `/var/run/docker.sock` and risk exposing the physical server to host takeover, **DOCKYARD** uses a nested **Docker-in-Docker (DinD)** design. 
All actions executed by players are fully trapped inside a nested virtual Docker engine. The host machine and any other running CTF challenges are 100% safe.

---

## Quick Start

```bash
# Build and launch the environment
docker compose up -d --build

# Verify all containers are online
docker compose ps
# Should show: jumpbox (running), jenkins (running), dind (running)

# Enter the player bastion jumpbox
docker exec -it jumpbox /bin/bash
```

---

## Challenge Architecture

```
                       ┌─────────────────┐
                       │    jumpbox      │ ◄── Player starts here
                       │  (172.28.0.10)  │     Has curl, jq, netcat
                       └────────┬────────┘
                                │
                                ▼ Pivots to
                       ┌─────────────────┐
                       │     jenkins     │ ◄── Web UI on host :8080
                       │  (172.28.0.20)  │     Runs pipeline builds
                       └────────┬────────┘
                                │
                         Accesses socket via
                            shared volume
                                │
                                ▼
                       ┌─────────────────┐
                       │      dind       │ ◄── Privileged daemon
                       │  (172.28.0.30)  │     (Docker-in-Docker)
                       └────────┬────────┘
                                │
                          Hosts isolated
                          nested container
                                │
                                ▼
                       ┌─────────────────┐
                       │  secure-vault   │ ◄── Nested inside dind
                       │                 │     Unreachable by network
                       │  🚩 Secret Flag │     Contains audit_token
                       └─────────────────┘
```

---

## Flag

```
nmctf{n3v3r_m0unt_d0ck3r_s0ck}
```

---

## File Structure

| File / Folder | Purpose |
| :--- | :--- |
| `docker-compose.yml` | Main orchestration setting up jumpbox, jenkins, and dind. |
| `jumpbox/` | Player entry container, motd banner, and developer_notes.txt. |
| `jenkins/` | Custom Jenkins LTS image with auto-configured admin account. |
| `dind/` | Sandboxed Docker-in-Docker engine and container-seeding script. |
| `CHALLENGE_DESCRIPTION.md` | Player-facing instructions and dynamic hints. |
| `SOLUTION.md` | In-depth writeup and explanation of raw socket queries. |

---

## Cleanup

```bash
docker compose down -v --rmi local
```
