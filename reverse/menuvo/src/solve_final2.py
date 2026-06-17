#!/usr/bin/env python3
import struct
import subprocess
from z3 import *

with open('/tmp/bytecode.bin', 'rb') as f:
    bytecode = f.read()

with open('/tmp/vmstate.bin', 'rb') as f:
    vmstate = f.read()

input_len = struct.unpack_from('<I', vmstate, 1660)[0]
print(f"Input length: {input_len}")

# Check what's in the VM memory area (offset 1056, 512 bytes)
vm_memory = vmstate[1056:1056+512]
print(f"VM memory first 64 bytes: {vm_memory[:64].hex()}")
print(f"VM memory[0] = {vm_memory[0]}")  # Should be input_len = 31 = 0x1F

# Check registers
for i in range(8):
    val = struct.unpack_from('<I', vmstate, i*4)[0]
    print(f"  r{i} = 0x{val:08x}")

# Check other state
print(f"  stack_ptr = {struct.unpack_from('<I', vmstate, 1568)[0]}")
print(f"  ip = {struct.unpack_from('<I', vmstate, 1572)[0]}")
print(f"  flag = {struct.unpack_from('<I', vmstate, 1576)[0]}")
print(f"  running = {struct.unpack_from('<I', vmstate, 1580)[0]}")

# The VM memory[0] should contain the input length (31 = 0x1F)
# And the input bytes should be in the VM state at offset 1596

# Now let's properly emulate with the correct initial state
def solve_vm(bytecode, input_len, initial_memory):
    inp = [BitVec(f'c{i}', 8) for i in range(input_len)]
    
    regs = [BitVecVal(0, 32) for _ in range(8)]
    # Initialize memory from the VM state dump
    memory = [BitVecVal(initial_memory[i], 8) for i in range(512)]
    stack = []
    call_stack = []
    ip = 0
    flag_reg = None  # None = unset, True/False = concrete, tuple = symbolic
    running = True
    constraints = []
    
    max_steps = 200000
    steps = 0
    
    while running and ip < len(bytecode) and steps < max_steps:
        steps += 1
        opcode = bytecode[ip]
        ip += 1
        
        if opcode == 0xFF:
            print(f"  HALT_FAIL at ip={ip-1}, step={steps}")
            running = False
            return None
            
        elif opcode == 0xFE:
            print(f"  HALT_SUCCESS at ip={ip-1}, step={steps}")
            running = False
            
        elif opcode == 0xF1:
            dst = bytecode[ip] & 7; ip += 1
            idx = bytecode[ip]; ip += 1
            if idx < input_len:
                regs[dst] = ZeroExt(24, inp[idx])
            else:
                regs[dst] = BitVecVal(0, 32)
                
        elif opcode == 23:  # load imm16
            dst = bytecode[ip] & 7; ip += 1
            lo = bytecode[ip]; ip += 1
            hi = bytecode[ip]; ip += 1
            regs[dst] = BitVecVal(lo | (hi << 8), 32)
            
        elif opcode == 35:  # push
            src = bytecode[ip] & 7; ip += 1
            stack.append(regs[src])
            
        elif opcode == 68:  # pop
            dst = bytecode[ip] & 7; ip += 1
            if stack:
                regs[dst] = stack.pop()
                
        elif opcode == 40 or opcode == 145:  # add
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] + regs[src2]
            
        elif opcode == 163:  # sub
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] - regs[src2]
            
        elif opcode == 114 or opcode == 131:  # mul
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] * regs[src2]
            
        elif opcode == 199 or opcode == 20:  # xor
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] ^ regs[src2]
            
        elif opcode == 31:  # or
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] | regs[src2]
            
        elif opcode == 8:  # and
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] & regs[src2]
            
        elif opcode == 170:  # shl
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = regs[src1] << (regs[src2] & 0x1F)
            
        elif opcode == 187:  # shr
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            regs[dst] = LShR(regs[src1], regs[src2] & 0x1F)
            
        elif opcode == 210:  # rol
            dst = bytecode[ip] & 7; ip += 1
            amt_byte = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt_byte & 31
            if n:
                regs[dst] = (val << n) | LShR(val, 32 - n)
                
        elif opcode == 229:  # ror
            dst = bytecode[ip] & 7; ip += 1
            amt_byte = bytecode[ip]; ip += 1
            val = regs[dst]
            n = amt_byte & 31
            if n:
                regs[dst] = LShR(val, n) | (val << (32 - n))
                
        elif opcode == 53:  # not
            dst = bytecode[ip] & 7; ip += 1
            regs[dst] = ~regs[dst]
            
        elif opcode == 63 or opcode == 126:  # cmp (set flag = r[a] == r[b])
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            a = simplify(regs[src1])
            b = simplify(regs[src2])
            # Try to evaluate concretely
            if is_bv_value(a) and is_bv_value(b):
                flag_reg = (a.as_long() == b.as_long())
            else:
                flag_reg = (regs[src1], regs[src2])  # symbolic
            
        elif opcode == 74:  # jump if flag (if equal)
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                # For the "good" path, we need this comparison to be TRUE
                constraints.append(a == b)
                ip += offset
            elif flag_reg == True:
                ip += offset
            # else: don't jump
                
        elif opcode == 92:  # jump if NOT flag (if not equal)
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            if isinstance(flag_reg, tuple):
                a, b = flag_reg
                # For the "good" path with JNE, we need comparison to be FALSE
                # But wait - in this VM, JNE jumps when flag==0 (not equal)
                # If we're on the success path, we should NOT jump (flag should be 1)
                # Actually it depends on context. Let me think...
                # 
                # The pattern is: CMP r0, r1; JNE skip_fail; FAIL
                # So if equal -> don't jump -> continue (good)
                # If not equal -> jump over fail code
                # 
                # Actually looking at the bytecode end: 0x7e 0x00 0x01 0x5c 0x01 0x00 0xfe 0xff
                # CMP r0, r1; JNE +0x0100; HALT_SUCCESS; HALT_FAIL
                # Wait that's: CMP r0,r1; if NOT equal jump +256; 0xFE(success); 0xFF(fail)
                # So if equal -> don't jump -> hit 0xFE (success)
                # If not equal -> jump +256 -> probably more code or fail
                #
                # For the initial check: 0x7e 0x00 0x02 0x5c 0x41 0x1b
                # CMP r0, r2; JNE +0x411B (jump far ahead if not equal)
                # So if r0 != r2, jump to near the end (probably fail)
                # We want r0 == r2, so DON'T jump
                # That means: add constraint a == b, DON'T take the jump
                constraints.append(a == b)
                # Don't jump - continue to next instruction
            elif flag_reg == False:
                ip += offset  # not equal, jump
            # else (flag_reg == True): don't jump
                
        elif opcode == 105:  # unconditional jump
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            ip += offset
            
        elif opcode == 184:  # call
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            call_stack.append(ip)
            ip += offset
            
        elif opcode == 45:  # ret
            if call_stack:
                ip = call_stack.pop()
                
        elif opcode == 107:  # store byte to memory
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            src = bytecode[ip] & 7; ip += 1
            addr = (hi << 8) | lo
            if addr < 512:
                memory[addr] = Extract(7, 0, regs[src])
                
        elif opcode == 82:  # load byte from memory
            dst = bytecode[ip] & 7; ip += 1
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            addr = (hi << 8) | lo
            if addr < 512:
                regs[dst] = ZeroExt(24, memory[addr])
            else:
                regs[dst] = BitVecVal(0, 32)
                
        elif opcode == 159:  # mod
            dst = bytecode[ip] & 7; ip += 1
            src1 = bytecode[ip] & 7; ip += 1
            src2 = bytecode[ip] & 7; ip += 1
            # Check if divisor is concrete and non-zero
            d = simplify(regs[src2])
            if is_bv_value(d) and d.as_long() == 0:
                pass  # skip division by zero
            else:
                regs[dst] = URem(regs[src1], regs[src2])
            
        elif opcode == 58:  # NOP
            pass
            
        else:
            print(f"  Unknown opcode 0x{opcode:02x} at ip={ip-1}, step={steps}")
            running = False
            return None
    
    if steps >= max_steps:
        print(f"  Exceeded max steps")
        return None
        
    print(f"  Total: {steps} steps, {len(constraints)} constraints")
    
    # Solve
    solver = Solver()
    for c in constraints:
        solver.add(c)
    
    # Printable ASCII
    for i in range(input_len):
        solver.add(inp[i] >= 0x20)
        solver.add(inp[i] <= 0x7e)
    
    print("  Checking satisfiability...")
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

print("\n--- Solving ---")
flag = solve_vm(bytecode, input_len, vm_memory)

if flag:
    print(f"\n*** SOLUTION: {flag}")
    result = subprocess.run(
        ['./menuvo'], 
        input=flag.encode() + b'\n', 
        capture_output=True, timeout=5,
        cwd='/home/hitler/menuvo'
    )
    output = result.stdout.decode(errors='replace')
    if 'granted' in output:
        print(f"\n*** VERIFIED FLAG: nmctf{{{flag}}}")
    else:
        print(f"Verification failed: {output[-100:]}")
else:
    print("\nFailed to solve")

