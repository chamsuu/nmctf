#!/usr/bin/env python3
import struct
import subprocess
from z3 import *

with open('/tmp/bytecode.bin', 'rb') as f:
    bytecode = f.read()

with open('/tmp/vmstate.bin', 'rb') as f:
    vmstate = f.read()

input_len = struct.unpack_from('<I', vmstate, 1660)[0]
vm_memory = vmstate[1056:1056+512]
print(f"Input length: {input_len}, VM memory[0]: {vm_memory[0]}")

def read_offset(bytecode, ip):
    """Read 2-byte offset with correct byte swap (little-endian)."""
    byte1 = bytecode[ip]      # "hi" in decompilation
    byte2 = bytecode[ip + 1]  # "lo" in decompilation
    # After bswap16: offset = (byte2 << 8) | byte1
    raw = (byte1 << 8) | byte2
    # bswap16
    offset = ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)
    # Treat as signed 16-bit
    if offset >= 0x8000:
        offset -= 0x10000
    return offset

def solve_vm(bytecode, input_len, initial_memory):
    inp = [BitVec(f'c{i}', 8) for i in range(input_len)]
    
    regs = [BitVecVal(0, 32) for _ in range(8)]
    memory = [BitVecVal(initial_memory[i], 8) for i in range(512)]
    stack = []
    call_stack = []
    ip = 0
    flag_reg = None
    running = True
    constraints = []
    
    max_steps = 200000
    steps = 0
    
    while running and ip < len(bytecode) and steps < max_steps:
        steps += 1
        opcode = bytecode[ip]
        ip += 1
        
        if opcode == 0xFF:
            running = False
            return None
        elif opcode == 0xFE:
            running = False
        elif opcode == 0xF1:
            dst = bytecode[ip] & 7; ip += 1
            idx = bytecode[ip]; ip += 1
            if idx < input_len:
                regs[dst] = ZeroExt(24, inp[idx])
            else:
                regs[dst] = BitVecVal(0, 32)
        elif opcode == 23:
            dst = bytecode[ip] & 7; ip += 1
            lo = bytecode[ip]; ip += 1
            hi = bytecode[ip]; ip += 1
            regs[dst] = BitVecVal(lo | (hi << 8), 32)
        elif opcode == 35:
            src = bytecode[ip] & 7; ip += 1
            stack.append(regs[src])
        elif opcode == 68:
            dst = bytecode[ip] & 7; ip += 1
            if stack:
                regs[dst] = stack.pop()
        elif opcode in (40, 145):  # add
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] + regs[s2]
        elif opcode == 163:  # sub
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] - regs[s2]
        elif opcode in (114, 131):  # mul
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] * regs[s2]
        elif opcode in (199, 20):  # xor
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] ^ regs[s2]
        elif opcode == 31:  # or
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] | regs[s2]
        elif opcode == 8:  # and
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] & regs[s2]
        elif opcode == 170:  # shl
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[s1] << (regs[s2] & 0x1F)
        elif opcode == 187:  # shr
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            regs[dst] = LShR(regs[s1], regs[s2] & 0x1F)
        elif opcode == 210:  # rol
            dst = bytecode[ip] & 7; ip += 1
            amt = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt & 31
            if n:
                regs[dst] = (val << n) | LShR(val, 32 - n)
        elif opcode == 229:  # ror
            dst = bytecode[ip] & 7; ip += 1
            amt = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt & 31
            if n:
                regs[dst] = LShR(val, n) | (val << (32 - n))
        elif opcode == 53:  # not
            dst = bytecode[ip] & 7; ip += 1
            regs[dst] = ~regs[dst]
        elif opcode in (63, 126):  # cmp
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            a = simplify(regs[s1])
            b = simplify(regs[s2])
            if is_bv_value(a) and is_bv_value(b):
                flag_reg = (a.as_long() == b.as_long())
            else:
                flag_reg = (regs[s1], regs[s2])
        elif opcode == 74:  # JE (jump if equal / flag set)
            offset = read_offset(bytecode, ip); ip += 2
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                constraints.append(a == b)
                ip += offset
            elif flag_reg == True:
                ip += offset
        elif opcode == 92:  # JNE (jump if not equal / flag not set)
            offset = read_offset(bytecode, ip); ip += 2
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                # JNE: jump if NOT equal. For success path, we want equal (don't jump)
                constraints.append(a == b)
                # DON'T jump
            elif flag_reg == False:
                ip += offset
        elif opcode == 105:  # unconditional jump
            offset = read_offset(bytecode, ip); ip += 2
            ip += offset
        elif opcode == 184:  # call
            offset = read_offset(bytecode, ip); ip += 2
            call_stack.append(ip)
            ip += offset
        elif opcode == 45:  # ret
            if call_stack:
                ip = call_stack.pop()
        elif opcode == 107:  # store to memory
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            src = bytecode[ip] & 7; ip += 1
            addr = (hi << 8) | lo
            # Apply bswap to address too
            addr = ((addr & 0xFF) << 8) | ((addr >> 8) & 0xFF)
            if addr < 512:
                memory[addr] = Extract(7, 0, regs[src])
        elif opcode == 82:  # load from memory
            dst = bytecode[ip] & 7; ip += 1
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            addr = (hi << 8) | lo
            addr = ((addr & 0xFF) << 8) | ((addr >> 8) & 0xFF)
            if addr < 512:
                regs[dst] = ZeroExt(24, memory[addr])
            else:
                regs[dst] = BitVecVal(0, 32)
        elif opcode == 159:  # mod
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            d = simplify(regs[s2])
            if is_bv_value(d) and d.as_long() == 0:
                pass
            else:
                regs[dst] = URem(regs[s1], regs[s2])
        elif opcode == 58:  # NOP
            pass
        else:
            print(f"  Unknown opcode 0x{opcode:02x} at ip={ip-1}, step={steps}")
            running = False
            return None
    
    if steps >= max_steps:
        print(f"  Exceeded max steps")
        return None
    
    print(f"  Finished: {steps} steps, {len(constraints)} constraints")
    
    solver = Solver()
    for c in constraints:
        solver.add(c)
    for i in range(input_len):
        solver.add(inp[i] >= 0x20)
        solver.add(inp[i] <= 0x7e)
    
    print("  Solving...")
    if solver.check() == sat:
        model = solver.model()
        result = ''
        for i in range(input_len):
            val = model.eval(inp[i], model_completion=True)
            result += chr(val.as_long())
        return result
    else:
        print("  UNSAT!")
        return None

print("--- Solving ---")
flag = solve_vm(bytecode, input_len, vm_memory)

if flag:
    print(f"\n*** SOLUTION: {flag}")
    result = subprocess.run(
        ['./menuvo'], input=flag.encode() + b'\n',
        capture_output=True, timeout=5, cwd='/home/hitler/menuvo'
    )
    output = result.stdout.decode(errors='replace')
    if 'granted' in output:
        print(f"\n*** VERIFIED FLAG: nmctf{{{flag}}}")
    else:
        print(f"Verification failed. Output: {output[-200:]}")
else:
    print("\nFailed to solve")

