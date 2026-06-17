# Challenge Writeups Index

All writeups are located in their respective challenge directories.

## Writeup Locations

### Challenge 01: Entry Gate (ARM32 - Easy)
**Path:** `challenges/01-entry-gate/WRITEUP.md`

**Topics Covered:**
- ARM32 buffer overflow
- Thumb mode interworking
- ARM32 calling convention (register-based arguments)
- ROP chain construction
- Stack layout analysis

**Key Learning:** ARM32 register-based arguments and Thumb mode state management.

---

### Challenge 02: Token Terminal (x86_32 - Medium)
**Path:** `challenges/02-token-terminal/WRITEUP.md`

**Topics Covered:**
- Integer truncation (16-bit to 32-bit cast)
- Heap overflow via controlled allocation sizes
- BSS data corruption (no PIE)
- Function pointer hijacking

**Key Learning:** Truncation errors can lead to out-of-bounds heap access even in O1-optimized code.

---

### Challenge 03: Staff Chat (x86_64 - Medium)
**Path:** `challenges/03-staff-chat/WRITEUP.md`

**Topics Covered:**
- Use-After-Free (UAF) in messaging objects
- XOR encryption reversal (glibc heap pointers)
- Tcache poisoning (__free_hook overwrite)
- Unsorted bin libc leak

**Key Learning:** XOR-based tcache protection is easily bypassed once a heap leak is obtained.

---

### Challenge 04: Power Grid (ARM64 - Hard)
**Path:** `challenges/04-power-grid/WRITEUP.md`

**Topics Covered:**
- Custom canary using modular arithmetic
- ARM64 PIE bypass (ASLR leak)
- Stack pivoting to BSS
- AArch64 ROP (gadget selection for system())

**Key Learning:** PIE and custom canaries require a multi-stage leak and pivot strategy on ARM64.

---

### Challenge 05: Vault Driver (Kernel x86_64 - Hard)
**Path:** `challenges/05-vault-driver/WRITEUP.md`

**Topics Covered:**
- Kernel Double-Fetch race conditions
- TOCTOU logic flaws in IOCTL handlers
- KASLR bypass via diagnostic /proc leak
- Data-only attacks (Cred overwriting)
- Bypassing SMEP, SMAP, and KPTI

**Key Learning:** A stable race condition provides a powerful primitive that bypasses control-flow mitigations.

---

## Summary Table

| Challenge | Architecture | Difficulty | Technique | Writeup |
|-----------|--------------|------------|------------|---------|
| 01 Entry Gate | ARM32 | Easy | ROP + Thumb | `01-entry-gate/WRITEUP.md` |
| 02 Token Terminal | x86_32 | Medium | Integer Overflow + BSS | `02-token-terminal/WRITEUP.md` |
| 03 Staff Chat | x86_64 | Medium | UAF + XOR + Tcache | `03-staff-chat/WRITEUP.md` |
| 04 Power Grid | ARM64 | Hard | PIE + Custom Canary + Pivot | `04-power-grid/WRITEUP.md` |
| 05 Vault Driver | Kernel x86_64 | Hard | Race Condition + Cred | `05-vault-driver/WRITEUP.md` |

## Accessing Writeups

```bash
# View any writeup
cat challenges/<challenge-dir>/WRITEUP.md
```