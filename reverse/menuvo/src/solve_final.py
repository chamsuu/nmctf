#!/usr/bin/env python3
import struct
import subprocess
from z3 import *

with open('/tmp/bytecode.bin', 'rb') as f:
    bytecode = f.read()

print(f"Bytecode: {len(bytecode)} bytes")

# Also dump VM state to get input length
with open('/tmp/vmstate.bin', 'rb') as f:
    vmstate = f.read()

# VM state structure offsets:
# 0-31: registers r0-r7 (4 bytes each)
# 32-1055: call stack (256 * 4 bytes)
# 1056-1567: memory (512 bytes)  
# 1568: stack pointer
# 1572: instruction pointer
# 1576: flag register
# 1580: running flag
# 1584: bytecode pointer (8 bytes)
# 1592: bytecode size (4 bytes)
# 1596-1659: input buffer (64 bytes)
# 1660: input length

input_len = struct.unpack_from('<I', vmstate, 1660)[0]
print(f"Input length: {input_len}")

# Read the input from VM state to verify
input_data = vmstate[1596:1596+input_len]
print(f"Input in VM state: {input_data}")

def solve_vm(bytecode, input_len):
    """Emulate VM with z3 symbolic input."""
    inp = [BitVec(f'c{i}', 8) for i in range(input_len)]
    
    regs = [BitVecVal(0, 32) for _ in range(8)]
    memory = [BitVecVal(0, 8) for _ in range(512)]
    stack = []
    call_stack = []  # separate from data stack based on VM semantics
    ip = 0
    flag_reg = False  # concrete boolean for now
    running = True
    constraints = []
    
    max_steps = 100000
    steps = 0
    
    while running and ip < len(bytecode) and steps < max_steps:
        steps += 1
        opcode = bytecode[ip]
        ip += 1
        
        if opcode == 0xFF:
            # Halt failure - this path should NOT be taken
            # Add constraint that we DON'T reach here
            print(f"  Hit HALT_FAIL at ip={ip-1}, step={steps}")
            running = False
            return None  # unsolvable on this path
            
        elif opcode == 0xFE:
            # Halt success!
            print(f"  Hit HALT_SUCCESS at ip={ip-1}, step={steps}")
            running = False
            
        elif opcode == 0xF1:
            # Load input byte
            dst = bytecode[ip] & 7; ip += 1
            idx = bytecode[ip]; ip += 1
            if idx < input_len:
                regs[dst] = ZeroExt(24, inp[idx])
            else:
                regs[dst] = BitVecVal(0, 32)
                
        elif opcode == 23:  # 0x17 - load imm16
            dst = bytecode[ip] & 7; ip += 1
            lo = bytecode[ip]; ip += 1
            hi = bytecode[ip]; ip += 1
            regs[dst] = BitVecVal(lo | (hi << 8), 32)
            
        elif opcode == 35:  # 0x23 - push
            src = bytecode[ip] & 7; ip += 1
            stack.append(regs[src])
            
        elif opcode == 68:  # 0x44 - pop
            dst = bytecode[ip] & 7; ip += 1
            if stack:
                regs[dst] = stack.pop()
                
        elif opcode == 40 or opcode == 145:  # 0x28/0x91 - add
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] + regs[src2]
            
        elif opcode == 163:  # 0xA3 - sub
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] - regs[src2]
            
        elif opcode == 114 or opcode == 131:  # 0x72/0x83 - mul
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] * regs[src2]
            
        elif opcode == 199 or opcode == 20:  # 0xC7/0x14 - xor
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] ^ regs[src2]
            
        elif opcode == 31:  # 0x1F - or
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] | regs[src2]
            
        elif opcode == 8:  # 0x08 - and
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] & regs[src2]
            
        elif opcode == 170:  # 0xAA - shl
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            shift_amt = regs[src2] & BitVecVal(0x1F, 32)
            regs[dst] = regs[src1] << shift_amt
            
        elif opcode == 187:  # 0xBB - shr
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            shift_amt = regs[src2] & BitVecVal(0x1F, 32)
            regs[dst] = LShR(regs[src1], shift_amt)
            
        elif opcode == 210:  # 0xD2 - rol
            dst = bytecode[ip] & 7; ip += 1
            amt_byte = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt_byte & 31
            if n:
                regs[dst] = (val << n) | LShR(val, 32 - n)
                
        elif opcode == 229:  # 0xE5 - ror
            dst = bytecode[ip] & 7; ip += 1
            amt_byte = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt_byte & 31
            if n:
                regs[dst] = LShR(val, n) | (val << (32 - n))
                
        elif opcode == 53:  # 0x35 - not
            dst = bytecode[ip] & 7; ip += 1
            regs[dst] = ~regs[dst]
            
        elif opcode == 63 or opcode == 126:  # 0x3F/0x7E - cmp
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            # Store symbolic comparison
            flag_reg = (regs[src1], regs[src2])  # tuple means symbolic
            
        elif opcode == 74:  # 0x4A - jump if flag set (if equal)
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                # We want the "good" path - assume comparison was true
                constraints.append(a == b)
                ip += offset
            elif flag_reg:
                ip += offset
                
        elif opcode == 92:  # 0x5C - jump if NOT flag (if not equal)
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                # We want the "good" path - assume comparison was false (not equal)
                constraints.append(a != b)
                ip += offset
            elif not flag_reg:
                ip += offset
                
        elif opcode == 105:  # 0x69 - unconditional jump
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            ip += offset
            
        elif opcode == 184:  # 0xB8 - call
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            call_stack.append(ip)
            ip += offset
            
        elif opcode == 45:  # 0x2D - ret
            if call_stack:
                ip = call_stack.pop()
                
        elif opcode == 107:  # 0x6B - store byte to memory
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            src = bytecode[ip] & 7; ip += 1
            addr = (hi << 8) | lo
            if addr < 512:
                memory[addr] = Extract(7, 0, regs[src])
                
        elif opcode == 82:  # 0x52 - load byte from memory
            dst = bytecode[ip] & 7; ip += 1
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            addr = (hi << 8) | lo
            if addr < 512:
                regs[dst] = ZeroExt(24, memory[addr])
            else:
                regs[dst] = BitVecVal(0, 32)
                
        elif opcode == 159:  # 0x9F - mod
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = URem(regs[src1], regs[src2])
            
        elif opcode == 58:  # 0x3A - NOP
            pass
            
        else:
            print(f"  Unknown opcode 0x{opcode:02x} at ip={ip-1}, step={steps}")
            running = False
            return None
    
    if steps >= max_steps:
        print(f"  Exceeded max steps ({max_steps})")
        return None
        
    print(f"  Finished: {steps} steps, {len(constraints)} constraints")
    
    # Solve
    solver = Solver()
    for c in constraints:
        solver.add(c)
    
    # Printable ASCII constraints
    for i in range(input_len):
        solver.add(inp[i] >= 0x20)
        solver.add(inp[i] <= 0x7e)
    
    print("  Solving...")
    if solver.check() == sat:
        model = solver.model()
        result = ''
        for i in range(input_len):
            val = model.eval(inp[i])
            if val.as_long() is not None:
                result += chr(val.as_long())
            else:
                result += '?'
        return result
    else:
        print("  UNSAT!")
        return None

# First, let's check what the first few bytes decode to
print(f"\nFirst 20 bytes of bytecode:")
for i in range(min(20, len(bytecode))):
    print(f"  [{i:4d}] 0x{bytecode[i]:02x}")

print(f"\nLast 10 bytes of bytecode:")
for i in range(len(bytecode)-10, len(bytecode)):
    print(f"  [{i:4d}] 0x{bytecode[i]:02x}")

print("\n--- Solving ---")
flag = solve_vm(bytecode, input_len)

if flag:
    print(f"\n*** SOLUTION: {flag}")
    # Verify
    result = subprocess.run(
        ['./menuvo'], 
        input=flag.encode() + b'\n', 
        capture_output=True, timeout=5,
        cwd='/home/hitler/menuvo'
    )
    output = result.stdout.decode(errors='replace')
    if 'granted' in output:
        print(f"*** VERIFIED! Flag: nmctf{{{flag}}}")
    else:
        print(f"Verification failed: {output}")
        # Maybe the flag IS nmctf{...} format as input
        print(f"Trying as-is: {flag}")
else:
    print("\nFailed to solve")

