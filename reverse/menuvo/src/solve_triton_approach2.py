#!/usr/bin/env python3
"""
solve_triton_approach2.py — Triton DSE with path predicate negation.

RESULT: DOES NOT WORK for this challenge.

Strategy: Run the binary concretely with dummy input (hits failure path).
Then use Triton's path predicate to negate the final branch condition,
asking "what input would make the JE at 0x4047A2 be TAKEN instead?"

WHY IT FAILS: The VM interpreter takes the failure path after the FIRST
character comparison fails. Concrete execution exits the VM loop early,
so only 1 of 31 input constraints propagates to the final branch.
The negated constraint is satisfiable but under-constrained.

This is a fundamental limitation of single-path DSE on VM-based challenges.
Use solve_triton_approach1.py (which intercepts VM-internal comparisons) instead.
"""
import sys, subprocess
from triton import *
import lief

BINARY = "./menuvo"
INPUT_LEN = 31

MAIN_FUNC    = 0x402EA0
TARGET_JE    = 0x4047A2  # je to success after VM
SUCCESS_ADDR = 0x4048F2
FAILURE_ADDR = 0x4047A8

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
    # NO ONLY_ON_SYMBOLIZED — we need full symbolic propagation

    print("[*] Loading binary...")
    load_binary(ctx)

    rsp = STACK_BASE + STACK_SIZE - 0x8000
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ret_addr = 0xDEAD0000
    rsp -= 8
    ctx.setConcreteRegisterValue(ctx.registers.rsp, rsp)
    ctx.setConcreteMemoryAreaValue(rsp, ret_addr.to_bytes(8, 'little'))
    ctx.setConcreteMemoryAreaValue(0x4B96B8, (0xCAFE).to_bytes(8, 'little'))

    ip = MAIN_FUNC
    count = 0

    print("[*] Emulating (full symbolic tracking — this will be slow)...")

    while count < 10000000:
        count += 1

        if ip == ret_addr:
            break

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

        # At the target JE: get the path predicate and negate it
        if ip == TARGET_JE:
            print(f"[+] Reached target JE at {count} instructions")
            # Process the JE instruction
            opcodes = ctx.getConcreteMemoryAreaValue(ip, 16)
            insn = Instruction(ip, bytes(opcodes))
            ctx.processing(insn)

            # The JE was NOT taken (concrete path = failure)
            # We want it TAKEN (success). Negate the last path constraint.
            pcs = ctx.getPathConstraints()
            if pcs:
                last_pc = pcs[-1]
                # Get the branch constraint for the "taken" path
                branches = last_pc.getBranchConstraints()
                for branch in branches:
                    if branch['isTaken'] == False:
                        # This is the path we WANT (taken = success)
                        target_constraint = branch['constraint']
                        print(f"[*] Negating path constraint...")

                        # Add printable ASCII bounds
                        ast_ctx = ctx.getAstContext()
                        extra = []
                        for i in range(INPUT_LEN):
                            sym = ctx.getSymbolicVariable(f"in_{i}")
                            if sym:
                                node = ast_ctx.variable(sym)
                                extra.append(ast_ctx.bvuge(node, ast_ctx.bv(0x20, 8)))
                                extra.append(ast_ctx.bvule(node, ast_ctx.bv(0x7e, 8)))

                        full = ast_ctx.land([target_constraint] + extra)
                        model = ctx.getModel(full)

                        if model:
                            flag = ['?'] * INPUT_LEN
                            for k, v in sorted(model.items()):
                                if k < INPUT_LEN:
                                    flag[k] = chr(v.getValue())
                            solution = ''.join(flag)
                            print(f"[+] Flag: {solution}")
                            print(f"    (model has {len(model)} variables)")

                            r = subprocess.run([BINARY], input=solution.encode() + b'\n',
                                             capture_output=True, timeout=5)
                            if b'granted' in r.stdout:
                                print("[+] VERIFIED ✓")
                            else:
                                print("[!] Verification failed — constraint was satisfiable")
                                print("    but doesn't properly constrain input (VM path issue)")
                            return
                        else:
                            print("[-] UNSAT on negated constraint")

                print("[-] Could not find suitable branch to negate")
                # Fallback: try using ZF directly
                zf = ctx.getRegisterAst(ctx.registers.zf)
                if zf.isSymbolized():
                    print("[*] Trying ZF == 1 directly...")
                    ast_ctx = ctx.getAstContext()
                    model = ctx.getModel(ast_ctx.equal(zf, ast_ctx.bv(1, 1)))
                    if model:
                        flag = ['?'] * INPUT_LEN
                        for k, v in sorted(model.items()):
                            sym = ctx.getSymbolicVariable(k)
                            if sym and sym.getName().startswith("in_"):
                                idx = int(sym.getName().split("_")[1])
                                flag[idx] = chr(v.getValue())
                        print(f"[+] Flag: {''.join(flag)}")
                    else:
                        print("[-] ZF not symbolized or UNSAT")
                else:
                    print("[-] ZF is concrete (not symbolic) — VM result didn't propagate")
                    print("    This approach requires the symbolic state to flow through")
                    print("    the entire VM execution, which doesn't happen because the")
                    print("    VM's internal branching (opcode dispatch) is concrete.")
                    print("")
                    print("    Use solve_triton_approach1.py or solve.py instead.")
                return

        opcodes = ctx.getConcreteMemoryAreaValue(ip, 16)
        insn = Instruction(ip, bytes(opcodes))
        ctx.processing(insn)
        ip = ctx.getConcreteRegisterValue(ctx.registers.rip)

        if count % 1000000 == 0:
            print(f"  ... {count//1000000}M instructions, ip=0x{ip:x}")

    print("[-] Did not reach target")


if __name__ == "__main__":
    main()
