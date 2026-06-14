# Challenge Writeups Index

All writeups are located in their respective challenge directories.

## Writeup Locations

### Challenge 01: Entry Gate Firmware (ARM32 - Easy)
**Path:** `challenges/01-entry-gate/WRITEUP.md`

**Topics Covered:**
- ARM32 buffer overflow
- Thumb mode interworking
- ARM32 calling convention (register-based arguments)
- ROP chain construction
- Stack layout analysis

**Key Learning:** ARM32 is different from x86_64 - arguments in registers, Thumb mode switching.

---

### Challenge 02: Token Exchange Terminal (x86_32 - Medium)
**Path:** `challenges/02-token-terminal/WRITEUP.md`

**Topics Covered:**
- Integer truncation overflow
- Heap overflow via integer overflow
- BSS overwrite (no PIE)
- Power-of-2 allocation constraints
- Function pointer corruption

**Key Learning:** Integer overflows can cause heap corruption even with safe-looking allocation.

---

### Challenge 03: Staff Chat Module (x86_64 - Medium)
**Path:** `challenges/03-staff-chat/WRITEUP.md`

**Topics Covered:**
- Use-After-Free (UAF) vulnerabilities
- XOR encryption reversal
- Chunk size field calculation
- Tcache manipulation (7-entry depth)
- Unsorted bin libc leak
- __free_hook overwrite

**Key Learning:** UAF provides powerful primitives when combined with heap understanding.

---

### Challenge 04: Arcade Power Grid Controller (ARM64 - Hard)
**Path:** `challenges/04-power-grid/WRITEUP.md`

**Topics Covered:**
- Custom canary reversal
- Modular inverse arithmetic
- Hidden diagnostic discovery
- ARM64 stack pivoting
- BSS ROP chain staging
- Frame size calculation

**Key Learning:** Custom protections require reverse engineering, ARM64 stack pivoting differs from x86_64.

---

### Challenge 05: Security Vault Driver (Kernel x86_64 - Hard)
**Path:** `challenges/05-vault-driver/WRITEUP.md`

**Topics Covered:**
- Kernel TOCTOU race conditions
- Double-fetch vulnerabilities
- KASLR bypass via /proc
- Cred struct spraying
- Data-only kernel attacks
- Modern kernel mitigations (SMEP, SMAP, KPTI)

**Key Learning:** Kernel exploitation with modern mitigations requires data-only approaches.

---

## Summary Table

| Challenge | Architecture | Difficulty | Technique | Writeup |
|-----------|--------------|------------|------------|---------|
| 01 Entry Gate | ARM32 | Easy | ROP + Thumb | `01-entry-gate/WRITEUP.md` |
| 02 Token Terminal | x86_32 | Medium | Integer Overflow + BSS | `02-token-terminal/WRITEUP.md` |
| 03 Staff Chat | x86_64 | Medium | UAF + XOR + Tcache | `03-staff-chat/WRITEUP.md` |
| 04 Power Grid | ARM64 | Hard | Custom Canary + Pivot | `04-power-grid/WRITEUP.md` |
| 05 Vault Driver | Kernel x86_64 | Hard | Race Condition + Cred | `05-vault-driver/WRITEUP.md` |

## Accessing Writeups

```bash
# Challenge 01
cat challenges/01-entry-gate/WRITEUP.md

# Challenge 02
cat challenges/02-token-terminal/WRITEUP.md

# Challenge 03
cat challenges/03-staff-chat/WRITEUP.md

# Challenge 04
cat challenges/04-power-grid/WRITEUP.md

# Challenge 05
cat challenges/05-vault-driver/WRITEUP.md
```

Each writeup includes:
- Detailed vulnerability analysis
- Binary protection information
- Step-by-step exploitation approach
- Exploit script breakdown with explanations
- Why the attack works
- Mitigation strategies