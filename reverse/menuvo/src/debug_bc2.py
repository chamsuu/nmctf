#!/usr/bin/env python3
import struct

with open('/tmp/bytecode.bin', 'rb') as f:
    bytecode = f.read()

# The JE at position 30 jumps to 801 (30 + 3 bytes for JE opcode + 768 offset)
# Wait: JE is at position 30, takes 3 bytes (opcode + 2 byte offset)
# After JE, ip = 33. Then offset = 768. So target = 33 + 768 = 801.
# But 801 has opcode 0x01 which is unknown!

# Let me check: the JE format from the VM code:
# opcode 0x4A: read 2 bytes for offset, then ip += offset
# So at position 30: opcode=0x4A, then bytes at 31,32 are the offset
# After reading offset, ip = 33. Then ip += offset.
# offset bytes: bytecode[31]=0x03, bytecode[32]=0x00
# offset = struct.unpack('>h', bytes([0x03, 0x00]))[0] = 768
# target = 33 + 768 = 801

# But wait - looking at the hex dump around 795-810:
# Position 795: 00 00 01 23 00 17 01 07 00 aa 02 00 01 17 01 19 00 bb 03 00
# Position 801 would be: 23 (which is PUSH!)

# Let me recount. The hex at position 795 is:
print(f"Bytes at 795-815: {bytecode[795:815].hex()}")
print(f"Byte at 800: 0x{bytecode[800]:02x}")
print(f"Byte at 801: 0x{bytecode[801]:02x}")

# Hmm, 801 = 0x23 which is PUSH, not 0x01!
# So my solver must have a bug in how it's computing the jump target.

# Let me re-examine: in my solver, for opcode 0x4A (JE):
# hi = bytecode[ip]; ip += 1
# lo = bytecode[ip]; ip += 1  
# offset = struct.unpack('>h', bytes([hi, lo]))[0]
# ip += offset

# At the JE instruction at position 30:
# bytecode[30] = 0x4A (the opcode)
# bytecode[31] = hi = 0x03
# bytecode[32] = lo = 0x00
# After reading: ip = 33
# offset = struct.unpack('>h', b'\x03\x00')[0] = 768
# ip = 33 + 768 = 801

# bytecode[801] should be... let me check
print(f"Byte at position 801: 0x{bytecode[801]:02x}")

# Actually wait, let me recount from the trace output:
# [30] JE +768 (-> 801)
# But the trace says target is 801. Let me verify:
# Position 30 is the JE opcode. ip becomes 31.
# Read hi=bytecode[31], lo=bytecode[32]. ip becomes 33.
# offset = (0x03 << 8) | 0x00 = 768... wait no.
# struct.unpack('>h', bytes([0x03, 0x00])) = 768
# target = 33 + 768 = 801

# So what's at 801?
print(f"\nBytes 799-810: {' '.join(f'{bytecode[i]:02x}' for i in range(799, 810))}")
print(f"Position 801 = 0x{bytecode[801]:02x}")

# AH WAIT. Let me look at the actual bytes at positions 30-33:
print(f"\nBytes at 30-35: {' '.join(f'{bytecode[i]:02x}' for i in range(30, 36))}")

# The issue might be that the JE offset calculation is wrong.
# In the VM code: 
# HIBYTE(v132) = byte1 (first byte read)
# LOBYTE(v132) = byte2 (second byte read)
# v131 = _byteswap_ushort(v132)
# ip += v131
#
# So: v132 = (byte1 << 8) | byte2 (since HIBYTE is set first, LOBYTE second)
# Then bswap16 swaps bytes: result = (byte2 << 8) | byte1
# So the ACTUAL offset = (lo << 8) | hi = (byte2 << 8) | byte1

# THAT'S THE BUG! The offset is byte-swapped!
# Let me recalculate:
# bytes at 31,32 = 0x03, 0x00
# v132 = (0x03 << 8) | 0x00 = 0x0300
# After bswap16: 0x0003
# So offset = 3, not 768!
# target = 33 + 3 = 36

print(f"\nCORRECTED: JE offset should be 3, target = 36")
print(f"Byte at 36: 0x{bytecode[36]:02x}")

# So the correct offset calculation is:
# Read byte1 (hi), byte2 (lo)
# v132 = (byte1 << 8) | byte2
# offset = bswap16(v132) = (byte2 << 8) | byte1
# Which is just: offset = (lo << 8) | hi = little-endian 16-bit!

# Let me verify with the first JNE at position 11:
# bytes at 12,13 = 0x41, 0x1B
# offset = (0x1B << 8) | 0x41 = 0x1B41 = 6977
# target = 14 + 6977 = 6991
# bytecode[6991] = 0xFF (HALT_FAIL) - that makes sense!
print(f"\nVerify JNE: offset bytes 0x41,0x1B -> offset = {(0x1B << 8) | 0x41} = {(0x1B << 8) | 0x41}")
print(f"Target = 14 + {(0x1B << 8) | 0x41} = {14 + (0x1B << 8) | 0x41}")
print(f"Byte at 6991: 0x{bytecode[6991]:02x}")  # Should be 0xFF

# And the JE at 30:
# bytes 31,32 = 0x03, 0x00
# offset = (0x00 << 8) | 0x03 = 3
# target = 33 + 3 = 36
print(f"\nJE at 30: offset = {(0x00 << 8) | 0x03} = 3, target = 36")
print(f"Byte at 36: 0x{bytecode[36]:02x}")

