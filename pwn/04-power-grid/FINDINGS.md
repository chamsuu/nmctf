# Challenge 04: Power Grid - Investigation Findings (Hardened)

## Overview
ARM64 PLC binary with a buffer overflow vulnerability. The challenge has been hardened with **PIE** and a **Binary Base Leak** to meet the difficulty requirements of a "Hard" challenge.

## Hardening Breakthrough: PIE & Execution Redirection
Initially, exploitation was attempted on a non-PIE binary where Pointer Authentication (PAC) was suspected as a blocker. Further analysis revealed that:
1.  **PIE is Enabled**: The binary uses ASLR for all segments.
2.  **PAC is inactive on hot paths**: `main()` and `handle_connection()` do not use `paciasp`/`autiasp` in their epilogues, allowing for stable return address hijacking.
3.  **Dynamic Linking**: The binary is dynamically linked (or static PIE), meaning `system` is reached via a PLT stub (`system@plt`).

## Binary Analysis

### Component Details
- **Architecture**: ARM64 (aarch64)
- **Protections**: Full RELRO, NX enabled, PIE enabled, No Stack Canary.
- **Vulnerability**: `memcpy` overflow in `handle_command` (inlined).

### Key Offsets (PIE-relative)
- `system@plt`:          0x0880
- `plc_emergency_dump`:  0x0B20 (The leak source)
- `stack_pivot`:         0x0B6C (`mov sp, x0; ldp x29, x30, [sp], #16; ldp x0, x1, [sp], #16; ret`)
- `g_command_buf (BSS)`: 0x20030

## Exploitation Strategy

### 1. The Information Leak
Command `0xFF` with an invalid checksum triggers `plc_emergency_dump`, which leaks:
- `SP`: Current stack pointer (useful for canary calculation).
- `TICK`: Current `g_tick` value.
- `PID`: Process ID (used in canary).
- `CODE`: Address of `plc_emergency_dump` (used to calculate `pie_base`).

### 2. Custom Canary Bypass
The canary is calculated as:
`canary = ((g_tick ^ PID ^ SP ^ 0xDEADBEEF) * 0x1337133713371337)`
Note: `g_tick` increments during the exploit (once for the config command, once during `handle_command` execution), so the calculation must account for the state at the time of validation.

### 3. Stack Pivot & Stability
ARM64 `system()` internals (like `fork` and `execve`) require significant stack space (~several KB).
- **Fix**: `g_command_buf` and `MAX_PACKET` were increased to 8KB.
- **Pivot**: The exploit pivots the stack to `BSS + 0x1E00`, providing ~7.5KB of writable stack room below the pivot point.
- **Chain**: A ROP chain is staged in BSS to load `x0` with the command address and return to `system@plt`.

## Technical Hurdles Resolved
- ✅ **Stack Alignment**: Ensuring `sp` remains 16-byte aligned during pivot.
- ✅ **PLT Redirection**: Redirecting control flow to the `system@plt` stub instead of absolute libc addresses.
- ✅ **ASLR Bypass**: Using the leaked function pointer to derive the base of the PIE binary.

---
**Status**: Challenge Hardened & Verified.
**Goal**: Mastery of ARM64 stack pivoting and PIE-gated exploitation.
