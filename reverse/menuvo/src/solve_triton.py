#!/usr/bin/env python3
"""
menuvo solver using Triton DSE.
Strategy: Load the binary, emulate from main, but intercept the VM's internal
comparison logic to force the success path and collect symbolic constraints.

The VM's CMP opcode (0x3F/0x7E) compares two VM registers and stores result
at vm_state+0x628 (offset 1576). The x86 code that implements this is around
0x406548 where it writes the comparison result. We intercept there.
"""
import sys, subprocess, struct, os, tempfile
from triton import *
import lief

BINARY = "./menuvo"
INPUT_LEN = 31

MAIN_FUNC = 0x402EA0
FOPEN     = 0x410EF0
FGETS     = 0x410BB0
FCLOSE    = 0x4108E0
PUTS      = 0x4110D0
PRINTF    = 0x40A610
STRLEN    = 0x4010A0
MEMSET    = 0x401078
MALLOC    = 0x41BF30
FREE      = 0x41C460
STRTOL    = 0x409A60
GETTIME   = 0x4069B0

# The VM's CMP result write: at 0x406548, it does:
#   mov [rax+0x628], ecx  where ecx = (reg_a == reg_b) ? 1 : 0
# We intercept the x86 CMP that feeds this (sete instruction)
# Actually let's find the exact pattern...
# From decompilation: *(_DWORD *)(a1 + 1576) = reg[s1] == reg[s2]
# This compiles to a cmp + sete + movzx + mov sequence

# The JE at 0x4065D6 checks if vm_flag == 0 (for VM opcode 0x4A "jump if flag")
# The JE at 0x406679 checks if vm_flag == 0 (for VM opcode 0x5C "jump if !flag")
VM_JE_CHECK  = 0x4065D6  # je after test eax,eax (for opcode 0x4A)
VM_JNE_CHECK = 0x406679  # test for opcode 0x5C

STACK_BASE = 0x7FFFFF000000
STACK_SIZE = 0x200000
heap_ptr   = 0x10000000

SKIP_FUNCS = {FCLOSE, PUTS, PRINTF, STRTOL, FREE}


def load_binary(ctx):
    binary = lief.parse(BINARY)
    for seg in binary.segments:
        if seg.type == lief.ELF.Segment.TYPE.LOAD and seg.physical_size > 0:
            ctx.setConcreteMemoryAreaValue(seg.virtual_address, bytes(seg.content))


def do_ret(ctx, rax=0):
    ctx.setConcreteRegisterValue(ctx.registers.rax, rax)
    rsp = ctx.getConcreteRegisterValue(ctx.registers.rsp)
    ret = int.from_bytes(ctx.getConcreteMemoryAreaValue(rsp, 8), 'little')
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp + 8)
    return ret


def emulate(ctx):
    global heap_ptr

    rsp = STACK_BASE + STACK_SIZE - 0x8000
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ctx.setConcreteRegisterValue(ctx.registers.rbp, rsp)
    ret_addr = 0xDEAD0000
    rsp -= 8
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ctx.setConcreteMemoryAreaValue(rsp, ret_addr.to_bytes(8, 'little'))
    ctx.setConcreteMemoryAreaValue(0x4B96B8, (0xCAFE).to_bytes(8, 'little'))

    ip = MAIN_FUNC
    count = 0
    max_insns = 10000000
    constraints = []
    ast_ctx = ctx.getAstContext()

    while count < max_insns:
        count += 1

        if ip == ret_addr:
            break

        # Hooks
        if ip == FOPEN:
            ip = do_ret(ctx, 0); continue
        if ip == FGETS:
            buf = ctx.getConcreteRegisterValue(ctx.registers.rdi)
            for i in range(INPUT_LEN):
                ctx.setConcreteMemoryValue(buf + i, ord('A'))
            ctx.setConcreteMemoryValue(buf + INPUT_LEN, ord('\n'))
            ctx.setConcreteMemoryValue(buf + INPUT_LEN + 1, 0)
            for i in range(INPUT_LEN):
                ctx.symbolizeMemory(MemoryAccess(buf + i, 1), f"in_{i}")
            ip = do_ret(ctx, buf); continue
        if ip == STRLEN:
            ip = do_ret(ctx, INPUT_LEN); continue
        if ip == MEMSET:
            dst = ctx.getConcreteRegisterValue(ctx.registers.rdi)
            val = ctx.getConcreteRegisterValue(ctx.registers.rsi) & 0xFF
            sz = ctx.getConcreteRegisterValue(ctx.registers.rdx)
            for i in range(min(sz, 0x10000)):
                ctx.setConcreteMemoryValue(dst + i, val)
            ip = do_ret(ctx, dst); continue
        if ip == MALLOC:
            size = ctx.getConcreteRegisterValue(ctx.registers.rdi)
            ptr = heap_ptr
            heap_ptr += (size + 0xF) & ~0xF
            for i in range(size):
                ctx.setConcreteMemoryValue(ptr + i, 0)
            ip = do_ret(ctx, ptr); continue
        if ip == GETTIME:
            ip = do_ret(ctx, 1000); continue
        if ip in SKIP_FUNCS:
            ip = do_ret(ctx, 0); continue

        # Success detection
        if ip == 0x4048F2:
            print(f"[+] Reached SUCCESS path at {count} instructions")
            return constraints

        # Failure detection
        if ip == 0x4047A8:  # lea rdi, "Access denied"
            print(f"[-] Hit FAILURE at {count} instructions")
            return None

        # Execute instruction
        opcodes = ctx.getConcreteMemoryAreaValue(ip, 16)
        insn = Instruction(ip, bytes(opcodes))
        ctx.processing(insn)

        next_ip = ctx.getConcreteRegisterValue(ctx.registers.rip)

        # Intercept VM's conditional branches that depend on symbolic state
        # These are JE/JNE instructions within the VM executor (0x405470-0x4069D0)
        if insn.isBranch() and insn.isConditionTaken() is not None:
            if 0x405470 <= ip <= 0x4069D0:
                # Check if the branch condition involves symbolic data
                # Get the condition AST from the path constraints
                zf_ast = ctx.getRegisterAst(ctx.registers.zf)
                if zf_ast.isSymbolized():
                    # This branch depends on input! Force success path.
                    # In the VM: comparisons should be EQUAL for success
                    # The VM flag register stores 1 if equal.
                    # The x86 code: test eax,eax; je ... 
                    # If eax (vm_flag) == 0 -> ZF=1 -> je taken (skip jump = bad for JE opcode)
                    # If eax (vm_flag) != 0 -> ZF=0 -> je not taken (do jump = good for JE opcode)
                    #
                    # For VM opcode 0x4A (jump if flag): we want flag=1, so eax!=0, ZF=0, je NOT taken
                    # For VM opcode 0x5C (jump if !flag): we want flag=1, so eax!=0, ZF=0, je NOT taken
                    #
                    # So for ALL symbolic branches in the VM, we want ZF=0 (not taken)
                    constraint = ast_ctx.equal(zf_ast, ast_ctx.bv(0, 1))
                    constraints.append(constraint)
                    # Force ZF=0 -> branch not taken -> fall through
                    ctx.setConcreteRegisterValue(ctx.registers.zf, 0)
                    next_ip = insn.getNextAddress()

        ip = next_ip

        if count % 1000000 == 0:
            print(f"  ... {count//1000000}M insns, ip=0x{ip:x}")

    print(f"[-] Loop ended at {count} insns, ip=0x{ip:x}")
    return constraints


def main():
    ctx = TritonContext(ARCH.X86_64)
    ctx.setMode(MODE.ALIGNED_MEMORY, True)
    ctx.setMode(MODE.AST_OPTIMIZATIONS, True)
    ctx.setMode(MODE.CONSTANT_FOLDING, True)

    print("[*] Loading binary...")
    load_binary(ctx)

    print("[*] Emulating (may take a few minutes)...")
    constraints = emulate(ctx)

    if constraints is None or len(constraints) == 0:
        print("[-] Failed")
        sys.exit(1)

    print(f"[+] Collected {len(constraints)} constraints")

    ast_ctx = ctx.getAstContext()
    all_constraints = constraints[:]

    # Add printable ASCII bounds
    for i in range(INPUT_LEN):
        sym = ctx.getSymbolicVariable(f"in_{i}")
        if sym:
            node = ast_ctx.variable(sym)
            all_constraints.append(ast_ctx.bvuge(node, ast_ctx.bv(0x20, 8)))
            all_constraints.append(ast_ctx.bvule(node, ast_ctx.bv(0x7e, 8)))

    combined = ast_ctx.land(all_constraints)

    print("[*] Solving...")
    model = ctx.getModel(combined)

    if not model:
        print("[-] UNSAT")
        sys.exit(1)

    flag = ['?'] * INPUT_LEN
    for k, v in sorted(model.items()):
        sym = ctx.getSymbolicVariable(k)
        name = sym.getName()
        if name.startswith("in_"):
            idx = int(name.split("_")[1])
            flag[idx] = chr(v.getValue())

    solution = ''.join(flag)
    print(f"[+] Flag: {solution}")

    r = subprocess.run([BINARY], input=solution.encode() + b'\n', capture_output=True, timeout=5)
    if b'granted' in r.stdout:
        print("[+] VERIFIED ✓")
    else:
        print("[!] Verification failed")


if __name__ == "__main__":
    main()
