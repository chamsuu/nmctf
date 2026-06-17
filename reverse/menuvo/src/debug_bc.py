#!/usr/bin/env python3
import struct

with open('/tmp/bytecode.bin', 'rb') as f:
    bytecode = f.read()

# Let me trace through the bytecode manually to find where we go wrong
# The issue is likely with the 0x52 opcode - let me check its format

# From the VM decompilation for opcode 0x52 (82):
# v10 = bytecode_ptr
# v11 = ip; ip += 1
# v135 = bytecode[ip]  -> register (1 byte)
# v12 = bytecode_ptr
# v13 = ip; ip += 1  
# HIBYTE(v134) = bytecode[ip]  -> high byte of address
# v14 = bytecode_ptr
# v15 = ip; ip += 1
# LOBYTE(v134) = bytecode[ip]  -> low byte of address
# v133 = bswap16(v134)  -> address = (hi << 8) | lo
# So format is: 0x52 <reg> <addr_hi> <addr_lo>

# And for opcode 0x6B (107) store:
# HIBYTE(v140) = byte1 -> high byte of address
# LOBYTE(v140) = byte2 -> low byte of address  
# byte3 -> register
# v139 = bswap16(v140) -> address
# So format is: 0x6B <addr_hi> <addr_lo> <reg>

# Let me trace execution step by step
def trace_vm(bytecode, max_steps=20):
    ip = 0
    steps = 0
    memory = bytearray(512)
    memory[0] = 31  # input length
    
    while ip < len(bytecode) and steps < max_steps:
        steps += 1
        opcode = bytecode[ip]
        start_ip = ip
        ip += 1
        
        if opcode == 0x17:  # load imm16
            dst = bytecode[ip] & 7; ip += 1
            lo = bytecode[ip]; ip += 1
            hi = bytecode[ip]; ip += 1
            print(f"  [{start_ip:4d}] LOAD_IMM r{dst} = 0x{(lo|(hi<<8)):04x}")
        elif opcode == 0x52:  # load from memory
            dst = bytecode[ip] & 7; ip += 1
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            addr = (hi << 8) | lo
            print(f"  [{start_ip:4d}] LOAD_MEM r{dst} = mem[0x{addr:04x}]")
        elif opcode == 0x7E or opcode == 0x3F:  # cmp
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] CMP r{s1}, r{s2}")
        elif opcode == 0x5C:  # jne
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            print(f"  [{start_ip:4d}] JNE +{offset} (-> {ip+offset})")
        elif opcode == 0x4A:  # je
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            print(f"  [{start_ip:4d}] JE +{offset} (-> {ip+offset})")
        elif opcode == 0x3A:  # nop
            print(f"  [{start_ip:4d}] NOP")
        elif opcode == 0x23:  # push
            src = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] PUSH r{src}")
        elif opcode == 0x44:  # pop
            dst = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] POP r{dst}")
        elif opcode == 0xF1:  # load input
            dst = bytecode[ip] & 7; ip += 1
            idx = bytecode[ip]; ip += 1
            print(f"  [{start_ip:4d}] LOAD_INPUT r{dst} = input[{idx}]")
        elif opcode == 0xAA:  # shl
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] SHL r{dst} = r{s1} << r{s2}")
        elif opcode == 0x1F:  # or
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] OR r{dst} = r{s1} | r{s2}")
        elif opcode == 0x6B:  # store to memory
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            src = bytecode[ip] & 7; ip += 1
            addr = (hi << 8) | lo
            print(f"  [{start_ip:4d}] STORE_MEM mem[0x{addr:04x}] = r{src}")
        elif opcode == 0x83:  # mul
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] MUL r{dst} = r{s1} * r{s2}")
        elif opcode == 0x72:  # mul (alias)
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] MUL r{dst} = r{s1} * r{s2}")
        elif opcode == 0xC7 or opcode == 0x14:  # xor
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] XOR r{dst} = r{s1} ^ r{s2}")
        elif opcode == 0x28 or opcode == 0x91:  # add
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] ADD r{dst} = r{s1} + r{s2}")
        elif opcode == 0xA3:  # sub
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] SUB r{dst} = r{s1} - r{s2}")
        elif opcode == 0xB8:  # call
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            print(f"  [{start_ip:4d}] CALL +{offset} (-> {ip+offset})")
        elif opcode == 0x2D:  # ret
            print(f"  [{start_ip:4d}] RET")
        elif opcode == 0xFF:
            print(f"  [{start_ip:4d}] HALT_FAIL")
            break
        elif opcode == 0xFE:
            print(f"  [{start_ip:4d}] HALT_SUCCESS")
            break
        elif opcode == 0xBB:  # shr
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] SHR r{dst} = r{s1} >> r{s2}")
        elif opcode == 0xD2:  # rol
            dst = bytecode[ip] & 7; ip += 1
            amt = bytecode[ip]; ip += 1
            print(f"  [{start_ip:4d}] ROL r{dst}, {amt}")
        elif opcode == 0xE5:  # ror
            dst = bytecode[ip] & 7; ip += 1
            amt = bytecode[ip]; ip += 1
            print(f"  [{start_ip:4d}] ROR r{dst}, {amt}")
        elif opcode == 0x35:  # not
            dst = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] NOT r{dst}")
        elif opcode == 0x9F:  # mod
            dst = bytecode[ip] & 7; ip += 1
            s1 = bytecode[ip] & 7; ip += 1
            s2 = bytecode[ip] & 7; ip += 1
            print(f"  [{start_ip:4d}] MOD r{dst} = r{s1} % r{s2}")
        elif opcode == 0x69:  # jmp
            hi = bytecode[ip]; ip += 1
            lo = bytecode[ip]; ip += 1
            offset = struct.unpack('>h', bytes([hi, lo]))[0]
            print(f"  [{start_ip:4d}] JMP +{offset} (-> {ip+offset})")
        else:
            print(f"  [{start_ip:4d}] UNKNOWN 0x{opcode:02x}")
            # Show context
            print(f"         Context: {bytecode[max(0,start_ip-5):start_ip+10].hex()}")
            break
    
    return ip

# Trace first 50 instructions
print("=== First 50 instructions ===")
trace_vm(bytecode, 50)

# Now let's look at what's around position 800
print(f"\n=== Bytecode around position 795-810 ===")
print(bytecode[795:815].hex())

