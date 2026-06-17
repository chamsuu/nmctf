#!/usr/bin/env python3
"""
solve_triton_approach1.py — Triton DSE with forced path at VM's CMP instruction.

RESULT: WORKS ✓ (solves in ~400K instructions, ~10 seconds)

Strategy: Emulate the binary at x86-64 level. At address 0x40653B (the x86 `cmp ecx,eax`
that implements the custom VM's CMP opcode), intercept the comparison. If either operand
is symbolic, collect the constraint ecx==eax and force the result to "equal" so execution
continues on the success path.

This effectively forces all VM-internal comparisons to pass while recording what values
the input bytes must have.
"""
import sys, subprocess
from triton import *
import lief

BINARY = "./menuvo"
INPUT_LEN = 31

MAIN_FUNC    = 0x402EA0
VM_CMP_ADDR  = 0x40653B  # cmp ecx, eax (VM's CMP opcode implementation)
VM_SETE_ADDR = 0x40653D  # sete al (result of comparison)
SUCCESS_ADDR = 0x4048F2   # lea rdi, "Access granted"
FAILURE_ADDR = 0x4047A8   # lea rdi, "Access denied"

HOOKS = {
    0x410EF0: ('fopen', 0),
    0x410BB0: ('fgets', None),
    0x4108E0: ('fclose', 0),
    0x4110D0: ('puts', 0),
    0x40A610: ('printf', 0),
    0x4010A0: ('strlen', INPUT_LEN),
    0x401078: ('memset', None),
    0x41BF30: ('malloc', None),
    0x41C460: ('free', 0),
    0x409A60: ('strtol', 0),
    0x4069B0: ('gettime', 1000),
}

STACK_BASE = 0x7FFFFF000000
STACK_SIZE = 0x200000
heap_ptr   = 0x10000000


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


def main():
    global heap_ptr
    ctx = TritonContext(ARCH.X86_64)
    ctx.setMode(MODE.ALIGNED_MEMORY, True)
    ctx.setMode(MODE.AST_OPTIMIZATIONS, True)
    ctx.setMode(MODE.CONSTANT_FOLDING, True)

    print("[*] Loading binary...")
    load_binary(ctx)

    # Setup stack
    rsp = STACK_BASE + STACK_SIZE - 0x8000
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ret_addr = 0xDEAD0000
    rsp -= 8
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ctx.setConcreteMemoryAreaValue(rsp, ret_addr.to_bytes(8, 'little'))
    ctx.setConcreteMemoryAreaValue(0x4B96B8, (0xCAFE).to_bytes(8, 'little'))

    ip = MAIN_FUNC
    count = 0
    constraints = []
    ast_ctx = ctx.getAstContext()

    print("[*] Emulating with VM CMP interception...")

    while count < 10000000:
        count += 1

        if ip == ret_addr:
            break
        if ip == SUCCESS_ADDR:
            print(f"[+] Reached SUCCESS at {count} instructions")
            break
        if ip == FAILURE_ADDR:
            print(f"[-] Hit FAILURE at {count} instructions")
            break

        # Function hooks
        if ip in HOOKS:
            name, retval = HOOKS[ip]
            if name == 'fgets':
                buf = ctx.getConcreteRegisterValue(ctx.registers.rdi)
                for i in range(INPUT_LEN):
                    ctx.setConcreteMemoryValue(buf + i, ord('A'))
                ctx.setConcreteMemoryValue(buf + INPUT_LEN, 10)
                ctx.setConcreteMemoryValue(buf + INPUT_LEN + 1, 0)
                for i in range(INPUT_LEN):
                    ctx.symbolizeMemory(MemoryAccess(buf + i, 1), f"in_{i}")
                ip = do_ret(ctx, buf)
            elif name == 'memset':
                dst = ctx.getConcreteRegisterValue(ctx.registers.rdi)
                val = ctx.getConcreteRegisterValue(ctx.registers.rsi) & 0xFF
                sz = ctx.getConcreteRegisterValue(ctx.registers.rdx)
                for i in range(min(sz, 0x10000)):
                    ctx.setConcreteMemoryValue(dst + i, val)
                ip = do_ret(ctx, dst)
            elif name == 'malloc':
                size = ctx.getConcreteRegisterValue(ctx.registers.rdi)
                ptr = heap_ptr
                heap_ptr += (size + 15) & ~15
                for i in range(size):
                    ctx.setConcreteMemoryValue(ptr + i, 0)
                ip = do_ret(ctx, ptr)
            else:
                ip = do_ret(ctx, retval if retval else 0)
            continue

        # KEY: Intercept VM's CMP instruction
        if ip == VM_CMP_ADDR:
            ecx_ast = ctx.getRegisterAst(ctx.registers.ecx)
            eax_ast = ctx.getRegisterAst(ctx.registers.eax)

            if ecx_ast.isSymbolized() or eax_ast.isSymbolized():
                # Collect constraint: ecx must equal eax for success
                constraints.append(ast_ctx.equal(ecx_ast, eax_ast))
                # Force ecx = eax concretely so sete produces 1
                eax_val = ctx.getConcreteRegisterValue(ctx.registers.eax)
                ctx.setConcreteRegisterValue(ctx.registers.ecx, eax_val)

        # Normal execution
        opcodes = ctx.getConcreteMemoryAreaValue(ip, 16)
        insn = Instruction(ip, bytes(opcodes))
        ctx.processing(insn)
        ip = ctx.getConcreteRegisterValue(ctx.registers.rip)

        if count % 1000000 == 0:
            print(f"  ... {count//1000000}M instructions, ip=0x{ip:x}")

    print(f"[+] Collected {len(constraints)} constraints from VM CMP interceptions")

    if not constraints:
        print("[-] No constraints collected")
        sys.exit(1)

    # Add printable ASCII bounds
    all_nodes = list(constraints)
    for i in range(INPUT_LEN):
        sym = ctx.getSymbolicVariable(f"in_{i}")
        if sym:
            node = ast_ctx.variable(sym)
            all_nodes.append(ast_ctx.bvuge(node, ast_ctx.bv(0x20, 8)))
            all_nodes.append(ast_ctx.bvule(node, ast_ctx.bv(0x7e, 8)))

    combined = ast_ctx.land(all_nodes)

    print("[*] Solving...")
    model = ctx.getModel(combined)

    if not model:
        print("[-] UNSAT")
        sys.exit(1)

    flag = ['?'] * INPUT_LEN
    for k, v in sorted(model.items()):
        if k < INPUT_LEN:
            flag[k] = chr(v.getValue())

    solution = ''.join(flag)
    print(f"[+] Flag: {solution}")

    r = subprocess.run([BINARY], input=solution.encode() + b'\n', capture_output=True, timeout=5)
    if b'granted' in r.stdout:
        print("[+] VERIFIED ✓")
    else:
        print("[!] Verification failed")


if __name__ == "__main__":
    main()
