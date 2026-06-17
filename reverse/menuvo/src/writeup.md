# menuvo - Reverse Engineering

**Flag:** `nmctf{v1rtu4l_m4ch1n3s_4r3_fun}`

## Overview

`menuvo` is a statically-linked x86-64 ELF binary that implements a custom virtual machine to validate user input. The binary prompts for a 31-character key and runs it through VM bytecode to verify correctness.

## Analysis

### Anti-Debug

The binary reads `/proc/self/status` and checks `TracerPid` to detect debuggers. If a debugger is attached, it silently alters behavior.

### Architecture

1. **Input** — Reads up to 64 bytes, strips newline, stores length in VM memory
2. **Bytecode Generation** — A loop (31 iterations) builds ~7KB of VM bytecode in a heap buffer. The bytecode is deterministic (independent of input).
3. **VM Execution** — `sub_405470` interprets the bytecode against a VM state containing 8 registers, a stack, 512 bytes of memory, and the input buffer.
4. **Result** — If the VM halts with opcode `0xFE`, the flag is valid. Opcode `0xFF` means failure.

### VM Instruction Set

| Opcode | Mnemonic | Description |
|--------|----------|-------------|
| 0x17 | LOAD_IMM | reg = imm16 |
| 0xF1 | LOAD_INPUT | reg = input[idx] |
| 0x52 | LOAD_MEM | reg = memory[addr] |
| 0x6B | STORE_MEM | memory[addr] = reg |
| 0x23 | PUSH | push reg |
| 0x44 | POP | pop reg |
| 0x28/0x91 | ADD | dst = src1 + src2 |
| 0xA3 | SUB | dst = src1 - src2 |
| 0x72/0x83 | MUL | dst = src1 * src2 |
| 0xC7/0x14 | XOR | dst = src1 ^ src2 |
| 0x1F | OR | dst = src1 \| src2 |
| 0x08 | AND | dst = src1 & src2 |
| 0xAA | SHL | dst = src1 << src2 |
| 0xBB | SHR | dst = src1 >> src2 |
| 0xD2 | ROL | reg = rol(reg, imm8) |
| 0xE5 | ROR | reg = ror(reg, imm8) |
| 0x35 | NOT | reg = ~reg |
| 0x3F/0x7E | CMP | flag = (r1 == r2) |
| 0x4A | JE | jump if flag |
| 0x5C | JNE | jump if !flag |
| 0x69 | JMP | unconditional jump |
| 0xB8 | CALL | push ip, jump |
| 0x2D | RET | pop ip |
| 0x9F | MOD | dst = src1 % src2 |
| 0x3A | NOP | no operation |
| 0xFE | HALT_OK | success |
| 0xFF | HALT_FAIL | failure |

**Note:** 16-bit offsets/addresses are stored big-endian then byte-swapped at runtime (effectively little-endian: `offset = (byte2 << 8) | byte1`).

## Solution

### Approach

1. **Dump bytecode** — Used GDB to break at `0x40478d` (after bytecode generation) and dump the 6992-byte buffer from `rbx`, along with the initialized VM state.

2. **Symbolic execution with z3** — Wrote a Python VM emulator using z3 BitVecs for the 31 input bytes. The emulator:
   - Executes concrete operations normally
   - On `CMP` with symbolic operands, records the comparison
   - On conditional jumps with symbolic flags, adds the equality constraint (success path requires all comparisons to pass)

3. **Solve** — z3 finds the unique satisfying assignment for all 31 constraints under printable ASCII bounds.

### Solver (key excerpt)

```python
from z3 import *

inp = [BitVec(f'c{i}', 8) for i in range(31)]
regs = [BitVecVal(0, 32) for _ in range(8)]
constraints = []

# ... VM emulation loop ...
# On symbolic CMP + JNE: constraints.append(regs[s1] == regs[s2])

solver = Solver()
for c in constraints:
    solver.add(c)
for i in range(31):
    solver.add(inp[i] >= 0x20, inp[i] <= 0x7e)

solver.check()  # sat
model = solver.model()
flag = ''.join(chr(model.eval(inp[i]).as_long()) for i in range(31))
# nmctf{v1rtu4l_m4ch1n3s_4r3_fun}
```

### Verification

```
$ echo 'nmctf{v1rtu4l_m4ch1n3s_4r3_fun}' | ./menuvo
[*] Initializing VM...
[?] Enter key: [*] Verifying...
[+] Access granted. Flag valid!
```
