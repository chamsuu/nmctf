# chall1 — M/o/Vfuscator side-channel (rev, medium)

A 32-bit Linux ELF built with the M/o/Vfuscator (every instruction is a
`mov`).  Disassembly is a sea of memory-to-memory moves driven by a
huge lookup table, so static recovery of the embedded flag is hard.
The intentional flaw is a **timing side channel** that lets an attacker
brute-force the flag character by character.

```
$ ./chall wrong
$ ./chall nmctf{m0v_th3_fl4g_l0rd}
correct
```

## Files

```
chall           - the 32-bit ELF challenge binary (M/o/Vfuscated)
src/chall.c     - source (with the timing oracle baked in)
tools/gen_flag.py - regenerates the BASE/ADD tables when you change the flag
solve.py        - reference side-channel solver
writeup.md      - solution walkthrough
description     - one-line spec
```

## Building

Requires the M/o/Vfuscator on `PATH` (i.e. `movcc`).

```sh
movcc src/chall.c -o chall
```

The binary weighs in at ~10 MB because the runtime ships its own
crtd dispatch and softfloat helpers.  Strip with `strip chall` if you
want to ship a smaller artefact.

## Difficulty

* Static analysis: hard.  No jumps in `main`, the secret is not stored
  as a contiguous string and `strings` / `grep` over the binary turn up
  nothing.  The two parallel tables `BASE` and `ADD` have to be summed
  to recover each flag byte, which is a (cheap) red herring that still
  shows up as raw `movl` constants in the disassembly.
* Dynamic analysis: a debugger will of course see the flag appear on
  the stack at runtime, but the intended solve is the side channel.
