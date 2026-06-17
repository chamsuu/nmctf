#!/usr/bin/env python3
"""
Solver: Use GDB to dump the bytecode buffer after generation, then emulate the VM.
"""
import subprocess
import struct
import os

# Use GDB to dump the bytecode after it's generated
# The bytecode is at address stored in v8 (rbx after the malloc call)
# After the loop at 0x404725, before calling sub_405470, the bytecode pointer
# is stored at v39 (offset 0x780 from rsp) and size at v40 (offset 0x788)
# 
# Better: set breakpoint at 0x40478d (the "Verifying..." print) and dump rbx

gdb_script = """
set pagination off
set confirm off
file ./menuvo
break *0x40478d
run <<< "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
# At this point, the bytecode has been generated
# v39 = bytecode ptr is at [rsp+0x780]
# v40 = bytecode size is at [rsp+0x788]  
# But easier: look at the VM state structure passed to sub_405470
# The call is: sub_405470(&v35) where v35 is at [rsp+0x150]
# VM state layout:
#   +1580: running flag (should be 1)
#   +1584: bytecode pointer (8 bytes)
#   +1592: bytecode size (4 bytes)
#   +1596: input buffer (64 bytes)
#   +1660: input length (4 bytes)
# 
# Actually looking at the code before the call:
# v39 = v8 (bytecode buffer pointer) stored at [rsp+0x780]
# v40 = v10 (bytecode size) stored at [rsp+0x788]
# The VM state is v35 at [rsp+0x150]
# 
# Let me just dump from the address in rdi (first arg to sub_405470)
set $vm = $rdi
# Print bytecode pointer and size
printf "VM state at: %p\\n", $vm
printf "Running: %d\\n", *(int*)($vm + 1580)
printf "Bytecode ptr: %p\\n", *(long long*)($vm + 1584)
printf "Bytecode size: %d\\n", *(int*)($vm + 1592)
printf "Input length: %d\\n", *(int*)($vm + 1660)
# Dump bytecode
set $bc = *(long long*)($vm + 1584)
set $sz = *(int*)($vm + 1592)
dump binary memory /tmp/bytecode.bin $bc ($bc + $sz)
# Also dump the full VM state
dump binary memory /tmp/vmstate.bin $vm ($vm + 1664)
printf "Dumped %d bytes of bytecode\\n", $sz
quit
"""

with open('/tmp/gdb_dump.txt', 'w') as f:
    f.write(gdb_script)

result = subprocess.run(
    ['gdb', '-batch', '-x', '/tmp/gdb_dump.txt'],
    capture_output=True, timeout=30,
    cwd='/home/hitler/menuvo'
)
print("GDB stdout:", result.stdout.decode(errors='replace'))
print("GDB stderr:", result.stderr.decode(errors='replace')[-500:])

# Check if bytecode was dumped
if os.path.exists('/tmp/bytecode.bin'):
    with open('/tmp/bytecode.bin', 'rb') as f:
        bytecode = f.read()
    print(f"\nBytecode size: {len(bytecode)} bytes")
    print(f"First 32 bytes: {bytecode[:32].hex()}")
    
    # Also load VM state
    with open('/tmp/vmstate.bin', 'rb') as f:
        vmstate = f.read()
    print(f"VM state size: {len(vmstate)} bytes")
    
    # Now emulate the VM with symbolic input using z3
    print("\n--- Emulating VM ---")
    
    from z3 import *
    
    def emulate_vm_z3(bytecode, input_len):
        """Emulate the VM with symbolic input bytes."""
        # Create symbolic input
        inp = [BitVec(f'inp_{i}', 8) for i in range(input_len)]
        
        # VM state
        regs = [BitVecVal(0, 32) for _ in range(8)]
        memory = [BitVecVal(0, 8) for _ in range(512)]
        stack = []
        ip = 0
        flag = BitVecVal(0, 32)
        running = True
        result_val = None
        
        # Load input into memory at offset 1596-32=... actually input is separate
        # Input is at vm_state + 1596, accessed by opcode 0xF1
        
        constraints = []
        max_steps = 50000
        steps = 0
        
        while running and ip < len(bytecode) and steps < max_steps:
            steps += 1
            opcode = bytecode[ip]
            ip += 1
            
            if opcode == 0xFF:
                # Halt with failure
                result_val = 0
                running = False
            elif opcode == 0xFE:
                # Halt with success
                result_val = 1
                running = False
            elif opcode == 0xF1:
                # Load input byte: reg[op1] = input[op2]
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
                regs[dst] = regs[src1] << (regs[src2] & 0x1F)
            elif opcode == 187:  # 0xBB - shr
                dst = bytecode[ip] & 7; ip += 1
                src1 = bytecode[ip] & 7; ip += 1
                src2 = bytecode[ip] & 7; ip += 1
                regs[dst] = LShR(regs[src1], regs[src2] & 0x1F)
            elif opcode == 210:  # 0xD2 - rol
                dst = bytecode[ip] & 7; ip += 1
                amt_byte = bytecode[ip]; ip += 1
                val = regs[dst]
                amt = BitVecVal(amt_byte & 31, 32)
                regs[dst] = (val << amt) | LShR(val, 32 - amt)
            elif opcode == 229:  # 0xE5 - ror
                dst = bytecode[ip] & 7; ip += 1
                amt_byte = bytecode[ip]; ip += 1
                val = regs[dst]
                amt = BitVecVal(amt_byte & 31, 32)
                regs[dst] = LShR(val, amt) | (val << (32 - amt))
            elif opcode == 53:  # 0x35 - not
                dst = bytecode[ip] & 7; ip += 1
                regs[dst] = ~regs[dst]
            elif opcode == 63 or opcode == 126:  # 0x3F/0x7E - cmp
                src1 = bytecode[ip] & 7; ip += 1
                src2 = bytecode[ip] & 7; ip += 1
                flag = If(regs[src1] == regs[src2], BitVecVal(1, 32), BitVecVal(0, 32))
            elif opcode == 74:  # 0x4A - jump if flag
                hi = bytecode[ip]; ip += 1
                lo = bytecode[ip]; ip += 1
                offset = struct.unpack('>h', bytes([hi, lo]))[0]
                # For concrete flag values, we can branch
                # For symbolic, we need to handle differently
                if is_true(simplify(flag == 1)):
                    ip += offset
                elif is_false(simplify(flag == 1)):
                    pass  # don't jump
                else:
                    # Symbolic flag - assume the "good" path (flag=1 means comparison passed)
                    # Add constraint that flag must be 1
                    constraints.append(flag == 1)
                    ip += offset
            elif opcode == 92:  # 0x5C - jump if NOT flag
                hi = bytecode[ip]; ip += 1
                lo = bytecode[ip]; ip += 1
                offset = struct.unpack('>h', bytes([hi, lo]))[0]
                if is_true(simplify(flag == 0)):
                    ip += offset
                elif is_false(simplify(flag == 0)):
                    pass
                else:
                    constraints.append(flag == 0)
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
                stack.append(BitVecVal(ip, 32))
                ip += offset
            elif opcode == 45:  # 0x2D - ret
                if stack:
                    ret_addr = stack.pop()
                    if is_bv_value(ret_addr):
                        ip = ret_addr.as_long()
                    else:
                        print(f"WARNING: symbolic return address at step {steps}")
                        running = False
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
                # Only do mod if divisor != 0
                regs[dst] = URem(regs[src1], regs[src2])
            elif opcode == 58:  # 0x3A - NOP
                pass
            else:
                print(f"Unknown opcode {opcode:#x} at ip={ip-1}, step={steps}")
                running = False
        
        print(f"VM finished after {steps} steps, ip={ip}, result={result_val}")
        if result_val == 1:
            print("VM reached SUCCESS path!")
        elif result_val == 0:
            print("VM reached FAILURE path")
        
        return inp, constraints, result_val, steps
    
    # Determine input length from VM state
    input_len_from_state = struct.unpack_from('<I', vmstate, 1660)[0]
    print(f"Input length from VM state: {input_len_from_state}")
    
    # The input we gave was 31 A's, so input_len should be 31
    # Let's try with 31 characters
    inp, constraints, result, steps = emulate_vm_z3(bytecode, 31)
    
    if constraints:
        print(f"\nCollected {len(constraints)} constraints")
        solver = Solver()
        for c in constraints:
            solver.add(c)
        # Add printable ASCII constraints
        for i in range(31):
            solver.add(inp[i] >= 0x20)
            solver.add(inp[i] <= 0x7e)
        
        if solver.check() == sat:
            model = solver.model()
            flag = ''.join(chr(model.eval(inp[i]).as_long()) for i in range(31))
            print(f"\nFlag: {flag}")
            
            # Verify
            result = subprocess.run(['./menuvo'], input=flag.encode() + b'\n', capture_output=True, timeout=5)
            if b'granted' in result.stdout:
                print(f"VERIFIED! Flag: nmctf{{{flag}}}")
            else:
                print(f"Verification failed. Output: {result.stdout.decode()}")
                # Try the flag as-is (maybe it includes nmctf{})
                print(f"Trying flag directly: {flag}")
        else:
            print("UNSAT - no solution found")
    else:
        print("No constraints collected - something went wrong with emulation")

else:
    print("Failed to dump bytecode")
