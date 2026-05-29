# nmCTF 2026 — Git Policy

## Repository
- **Remote:** `https://github.com/chamsuu/nmctf` (private)
- **Tracker:** Git (local + GitHub)

---

## Branches

| Branch | Remote | Purpose |
|---|---|---|
| `master` | ✅ Pushed | Stable challenge files (chall.py, Dockerfile, flag.txt, challenge.yml, dist/) |
| `local` | ❌ Never pushed | Full local snapshot including solution/ folders, writeups, logs |
| `dev/crypto-chall` | ❌ Never pushed | Development — build new challenges, experiment, refactor |

### Workflow

```
dev/crypto-chall  ──►  master  ──►  origin/master
     │
     │  (build new challenge)
     │
     ▼
  git checkout master
  git merge dev/crypto-chall   (only after challenge is complete)
  git push origin master

local (full snapshot, never merge anywhere)
```

---

## What Goes Where

### `master` (pushed to remote)
```
crypto/<challenge>/
├── challenge.yml       # CTFd metadata
├── Dockerfile          # Only if server-based
├── dist/
│   ├── chall.py        # Player-facing code
│   └── output.txt      # Sample output
├── flag.txt            # Real flag (repo is private)
├── src/                # Source (optional)
└── admin/              # Admin info (optional)
```

### `local` (never pushed — full snapshot)
Everything in `master` **plus**:
```
crypto/<challenge>/solution/
├── solve.py
├── WRITEUP.md
├── hints.json
└── gen.py
*.log                    # Session/error logs
```

---

## Safety Rules

1. **No force push** without explicit confirmation from another collaborator
2. **Always check `git status`** before destructive operations (reset, delete, force push)
3. **Commit early, commit often** — every working state should be saved to at least `local`
4. **`dev/crypto-chall` → `master` merge** only when a challenge is fully built and tested
5. **`local` is your safety net** — if you delete something by accident, check `local` first

---

## Quick Reference

```bash
# Daily work (start here)
git checkout dev/crypto-chall

# Save your work (including solutions)
git checkout local
git add --all
git commit -m "local: snapshot <date>"
git checkout dev/crypto-chall   # or master

# Push a finished challenge to remote
git checkout master
git merge dev/crypto-chall
git push origin master

# Check what branch you're on
git branch --show-current

# See all branches
git branch -a

# See what files are tracked vs ignored
git ls-files --others --ignored --exclude-standard  # ignored files
git ls-tree --name-only -r HEAD                      # tracked files
```
