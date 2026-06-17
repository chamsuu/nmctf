#!/usr/bin/env python3
import subprocess
import struct
import os

# From the decompilation at 0x404795: sub_405470(&v35)
# v35 is at [rsp+0x150]
# But the call to sub_4110D0("Verifying") is at 0x40478d, BEFORE the call to sub_405470
# After the print, at 0x404795, the lea instruction loads &v35 into rdi
# Let's break at 0x404795 instead (the call to sub_405470)

# Actually, looking at the register dump:
# rbx = 0x4c4f20 -> this is the bytecode buffer (from malloc)
# rax = 0x1b50 -> this might be the bytecode size
# The bytecode is stored at [rsp+0x770] = rbx, size at [rsp+0x778] = eax

# Let me break right before sub_405470 call and dump from rbx with size from stack

gdb_script = """
set pagination off
set confirm off
file ./menuvo
# Break at the call to sub_405470 (the VM executor)
break *0x404795
run <<< "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
# rbx should still have the bytecode pointer
# The size was stored at [rsp+0x778] before
printf "Bytecode buffer at rbx: %p\\n", $rbx
# Read size from [rsp+0x778]  
set $sz = *(int*)($rsp + 0x778)
printf "Bytecode size from stack: %d (0x%x)\\n", $sz, $sz
# Also check what rdi points to (should be &v35 = VM state)
printf "RDI (VM state): %p\\n", $rdi
# Dump bytecode from rbx
dump binary memory /tmp/bytecode.bin $rbx ($rbx + $sz)
# Dump full VM state from rdi
dump binary memory /tmp/vmstate.bin $rdi ($rdi + 1664)
printf "Done dumping\\n"
quit
"""

with open('/tmp/gdb_dump2.txt', 'w') as f:
    f.write(gdb_script)

result = subprocess.run(
    ['gdb', '-batch', '-x', '/tmp/gdb_dump2.txt'],
    capture_output=True, timeout=30,
    cwd='/home/hitler/menuvo'
)

# Extract useful info from output
output = result.stdout.decode(errors='replace')
for line in output.split('\n'):
    if 'Bytecode' in line or 'size' in line or 'RDI' in line or 'Done' in line or 'Error' in line:
        print(line)

stderr = result.stderr.decode(errors='replace')
if 'Error' in stderr:
    print("STDERR:", stderr[-300:])

if os.path.exists('/tmp/bytecode.bin'):
    with open('/tmp/bytecode.bin', 'rb') as f:
        bytecode = f.read()
    print(f"\nBytecode dumped: {len(bytecode)} bytes")
    print(f"First 64 bytes hex: {bytecode[:64].hex()}")
    print(f"Last 16 bytes hex: {bytecode[-16:].hex()}")
else:
    print("Bytecode dump failed, trying alternative approach...")
    # Try breaking after the loop and reading rbx directly
    gdb_script2 = """
set pagination off
set confirm off
file ./menuvo
break *0x404792
run <<< "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
printf "rbx=%p rax=0x%x\\n", $rbx, $rax
# The bytecode was stored at [rsp+0x770]
set $bc_ptr = *(long long*)($rsp + 0x770)
set $bc_sz = *(int*)($rsp + 0x778)
printf "bc_ptr=%p bc_sz=%d\\n", $bc_ptr, $bc_sz
# Try dumping from rbx with a reasonable size
dump binary memory /tmp/bytecode.bin $rbx ($rbx + 0x2000)
quit
"""
    with open('/tmp/gdb_dump3.txt', 'w') as f:
        f.write(gdb_script2)
    result = subprocess.run(
        ['gdb', '-batch', '-x', '/tmp/gdb_dump3.txt'],
        capture_output=True, timeout=30,
        cwd='/home/hitler/menuvo'
    )
    output = result.stdout.decode(errors='replace')
    for line in output.split('\n'):
        if 'rbx' in line or 'bc_' in line or 'Error' in line:
            print(line)
    
    if os.path.exists('/tmp/bytecode.bin'):
        with open('/tmp/bytecode.bin', 'rb') as f:
            bytecode = f.read()
        print(f"Bytecode dumped (full buffer): {len(bytecode)} bytes")
        # Find the actual end (look for 0xFE 0xFF pattern or just use the size from earlier)
        # From GDB output earlier, rax was 0x1b50 at the verifying breakpoint
        # Let's trim to that
        bytecode = bytecode[:0x1b50]
        print(f"Trimmed to 0x1b50 = {len(bytecode)} bytes")
        print(f"First 32 bytes: {bytecode[:32].hex()}")
        with open('/tmp/bytecode.bin', 'wb') as f:
            f.write(bytecode)

