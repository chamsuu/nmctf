# 🐳 DOCKYARD

**Category:** Misc / DevSecOps
**Difficulty:** Medium-Hard
**Points:** 500
**Author:** 4mdj4d 

---

### Description

We’ve successfully compromised a low-privilege developer bastion inside the Algerian Devs internal network.
Their systems engineer,  has no idea we are here. He forgot to clean up the cached developer notes in this workspace.  look closely at what he left behind, hijack their internal automation servers, and plunder the secure vault.

---

### Connection

SSH :
ctf@app.alpha.openscaler.net -p 9134
Password: numidian123
---

### Hints

1/ Check your home directory. Developers often leave temporary credentials or deployment notes behind in their text files.


2/ Jenkins has a web panel exposed on the network. Once you find the developer's credentials, log into the panel and create a pipeline job that runs shell commands.


3/ Where is the build running? Check the build runner's environment. Are there any Unix domain socket files mounted inside `/var/

4/ If the Docker socket is mounted but there is no `docker` CLI tool installed, you can talk directly to the Docker Engine HTTP API using raw `curl` commands over the Unix socket. Check the Docker Engine API docs for listing containers and copying archives!

---

*Flag format:* `nmctf{...}`
