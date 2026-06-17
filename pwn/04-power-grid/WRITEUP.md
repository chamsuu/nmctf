# Challenge 04: Power Grid Controller - Writeup (PIE Edition)

## Summary
`plc` is an ARM64 PIE service that manages power grid operations. It uses a custom packet-based protocol and implements several security layers, including a custom reversible canary and a stack-checking mechanism.

## Vulnerability: Stack-based Buffer Overflow
The vulnerability exists in the `handle_command` function (inlined into `handle_connection`). A `memcpy` call uses a length derived from the network packet without validating it against the size of the destination buffer (`cmd_buf[128]`). 

```c
// Vulnerable Code
memcpy((void *)frame.cmd_buf, packet + 4, copy_len);
```

By sending a large packet, an attacker can overwrite the `command_frame_t` structure, which contains:
- `canary`: A 64-bit custom security token.
- `pivot`: A function pointer intended for emergency redirection.
- `pivot_arg`: The argument to be passed to the pivot function.

## Security Mitigations
- **PIE (Position Independent Executable)**: All binary addresses are randomized.
- **Custom Canary**: A dynamic token based on PID, SP, and Tick.
- **NX (No-Execute)**: The stack and BSS are non-executable.

## Exploitation Path

### 1. The Leak (ASLR Bypass)
Trigger the "Emergency Diagnostic" via command `0xFF` with an incorrect checksum. This leaks the address of `plc_emergency_dump`, allowing calculation of the binary's base address and the locations of gadgets/BSS.

### 2. Canary Calculation
Reversing the `generate_canary` function reveals that the canary is predictable if the SP, PID, and Tick are known (all of which are leaked in step 1).

### 3. BSS Staging & Stack Pivot
Since the overflow is forward-writing and the return address is protected by PAC-lite mechanisms in some paths, the most stable approach is to use the provided `stack_pivot` gadget.
1. Use the `Config` command to stage a ROP chain and the `/bin/sh` command string in the 8KB `g_command_buf` (BSS).
2. Trigger the overflow to overwrite `pivot` with `stack_pivot` and `pivot_arg` with the address of the staged ROP chain.

### 4. ROP to System
The `stack_pivot` gadget sets `SP` to our controlled BSS region. Because `system()` requires significant stack space, we place our chain near the end of the 8KB buffer, giving it ~7.5KB of room to grow downward without causing a page fault.

## FLAG: `FLAG{ROP_TO_SYSTEM_AARCH64_SUCCESS}`
