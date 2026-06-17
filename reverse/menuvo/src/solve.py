#!/usr/bin/env python3
"""
menuvo CTF solver — dumps VM bytecode via GDB, then solves with z3 symbolic execution.
Requirements: gdb, python3, z3-solver (pip install z3-solver)
"""

import subprocess, struct, tempfile, os, sys
from z3 import *

BINARY = "./menuvo"
DUMMY_INPUT = "A" * 31


def dump_bytecode():
    """Use GDB to run the binary and dump bytecode + VM state from memory."""
    bc_path = tempfile.mktemp(suffix=".bin")
    vm_path = tempfile.mktemp(suffix=".bin")

    gdb_script = f"""
set pagination off
set confirm off
file {BINARY}
break *0x40478d
run <<< "{DUMMY_INPUT}"
set $sz = *(int*)($rsp + 0x778)
dump binary memory {bc_path} $rbx ($rbx + $sz)
set $vm = $rsp + 0x140
dump binary memory {vm_path} $vm ($vm + 1664)
quit
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".gdb", delete=False) as f:
        f.write(gdb_script)
        gdb_file = f.name

    result = subprocess.run(
        ["gdb", "-batch", "-x", gdb_file],
        capture_output=True,
        timeout=30,
        cwd=os.path.dirname(os.path.abspath(BINARY)) or ".",
    )
    os.unlink(gdb_file)

    if not os.path.exists(bc_path):
        print("ERROR: GDB failed to dump bytecode")
        print(result.stderr.decode(errors="replace")[-500:])
        sys.exit(1)

    with open(bc_path, "rb") as f:
        bytecode = f.read()
    with open(vm_path, "rb") as f:
        vmstate = f.read()
    os.unlink(bc_path)
    os.unlink(vm_path)

    input_len = struct.unpack_from("<I", vmstate, 1660)[0]
    vm_memory = vmstate[1056 : 1056 + 512]
    print(f"[+] Dumped {len(bytecode)} bytes of bytecode, input_len={input_len}")
    return bytecode, input_len, vm_memory


def read_offset(bytecode, ip):
    """Read 2-byte jump offset (stored big-endian, then bswap'd = effectively little-endian)."""
    b1, b2 = bytecode[ip], bytecode[ip + 1]
    offset = (b2 << 8) | b1
    if offset >= 0x8000:
        offset -= 0x10000
    return offset


def solve_vm(bytecode, input_len, initial_memory):
    """Symbolically execute the VM and solve for input."""
    inp = [BitVec(f"c{i}", 8) for i in range(input_len)]
    regs = [BitVecVal(0, 32) for _ in range(8)]
    memory = [BitVecVal(initial_memory[i], 8) for i in range(512)]
    stack, call_stack, constraints = [], [], []
    ip, running = 0, True

    while running and ip < len(bytecode):
        op = bytecode[ip]
        ip += 1

        if op == 0xFF:
            return None  # hit failure path
        elif op == 0xFE:
            break  # success
        elif op == 0xF1:  # load input byte
            d = bytecode[ip] & 7
            ip += 1
            idx = bytecode[ip]
            ip += 1
            regs[d] = ZeroExt(24, inp[idx]) if idx < input_len else BitVecVal(0, 32)
        elif op == 23:  # load imm16
            d = bytecode[ip] & 7
            ip += 1
            lo = bytecode[ip]
            ip += 1
            hi = bytecode[ip]
            ip += 1
            regs[d] = BitVecVal(lo | (hi << 8), 32)
        elif op == 35:  # push
            stack.append(regs[bytecode[ip] & 7])
            ip += 1
        elif op == 68:  # pop
            d = bytecode[ip] & 7
            ip += 1
            if stack:
                regs[d] = stack.pop()
        elif op in (40, 145):  # add
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] + regs[b]
        elif op == 163:  # sub
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] - regs[b]
        elif op in (114, 131):  # mul
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] * regs[b]
        elif op in (199, 20):  # xor
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] ^ regs[b]
        elif op == 31:  # or
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] | regs[b]
        elif op == 8:  # and
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] & regs[b]
        elif op == 170:  # shl
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = regs[a] << (regs[b] & 0x1F)
        elif op == 187:  # shr
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            regs[d] = LShR(regs[a], regs[b] & 0x1F)
        elif op == 210:  # rol
            d = bytecode[ip] & 7
            ip += 1
            n = bytecode[ip] & 31
            ip += 1
            if n:
                regs[d] = (regs[d] << n) | LShR(regs[d], 32 - n)
        elif op == 229:  # ror
            d = bytecode[ip] & 7
            ip += 1
            n = bytecode[ip] & 31
            ip += 1
            if n:
                regs[d] = LShR(regs[d], n) | (regs[d] << (32 - n))
        elif op == 53:  # not
            d = bytecode[ip] & 7
            ip += 1
            regs[d] = ~regs[d]
        elif op in (63, 126):  # cmp
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            sa, sb = simplify(regs[a]), simplify(regs[b])
            flag_reg = (
                (sa.as_long() == sb.as_long())
                if (is_bv_value(sa) and is_bv_value(sb))
                else (regs[a], regs[b])
            )
        elif op == 74:  # je
            offset = read_offset(bytecode, ip)
            ip += 2
            if isinstance(flag_reg, tuple):
                constraints.append(flag_reg[0] == flag_reg[1])
                ip += offset
            elif flag_reg:
                ip += offset
        elif op == 92:  # jne
            offset = read_offset(bytecode, ip)
            ip += 2
            if isinstance(flag_reg, tuple):
                constraints.append(flag_reg[0] == flag_reg[1])  # success = don't jump
            elif not flag_reg:
                ip += offset
        elif op == 105:  # jmp
            offset = read_offset(bytecode, ip)
            ip += 2
            ip += offset
        elif op == 184:  # call
            offset = read_offset(bytecode, ip)
            ip += 2
            call_stack.append(ip)
            ip += offset
        elif op == 45:  # ret
            if call_stack:
                ip = call_stack.pop()
        elif op == 107:  # store mem
            h = bytecode[ip]
            ip += 1
            l = bytecode[ip]
            ip += 1
            s = bytecode[ip] & 7
            ip += 1
            addr = (l << 8) | h
            if addr < 512:
                memory[addr] = Extract(7, 0, regs[s])
        elif op == 82:  # load mem
            d = bytecode[ip] & 7
            ip += 1
            h = bytecode[ip]
            ip += 1
            l = bytecode[ip]
            ip += 1
            addr = (l << 8) | h
            regs[d] = ZeroExt(24, memory[addr]) if addr < 512 else BitVecVal(0, 32)
        elif op == 159:  # mod
            d = bytecode[ip] & 7
            ip += 1
            a = bytecode[ip] & 7
            ip += 1
            b = bytecode[ip] & 7
            ip += 1
            dv = simplify(regs[b])
            if not (is_bv_value(dv) and dv.as_long() == 0):
                regs[d] = URem(regs[a], regs[b])
        elif op == 58:  # nop
            pass
        else:
            print(f"[-] Unknown opcode 0x{op:02x} at {ip - 1}")
            return None

    print(f"[+] Collected {len(constraints)} constraints")
    solver = Solver()
    for c in constraints:
        solver.add(c)
    for i in range(input_len):
        solver.add(inp[i] >= 0x20, inp[i] <= 0x7E)

    if solver.check() != sat:
        print("[-] UNSAT")
        return None

    model = solver.model()
    return "".join(
        chr(model.eval(inp[i], model_completion=True).as_long())
        for i in range(input_len)
    )


def main():
    print("[*] Dumping bytecode via GDB...")
    bytecode, input_len, vm_memory = dump_bytecode()

    print("[*] Solving with z3...")
    flag = solve_vm(bytecode, input_len, vm_memory)

    if not flag:
        print("[-] Failed to solve")
        sys.exit(1)

    print(f"[+] Solution: {flag}")

    # Verify
    result = subprocess.run(
        [BINARY], input=flag.encode() + b"\n", capture_output=True, timeout=5
    )
    if b"granted" in result.stdout:
        print(f"[+] VERIFIED ✓")
    else:
        print(f"[!] Verification failed")


if __name__ == "__main__":
    main()
