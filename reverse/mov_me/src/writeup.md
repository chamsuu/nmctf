# Writeup — M/o/Vfuscator side channel

## TL;DR

`chall` is a 32-bit ELF compiled with the M/o/Vfuscator.  Every
instruction is a `mov`; `objdump -d chall` shows a lookup-table
dispatch in `main` and zero conditional branches.  The flag is
reconstructed at runtime from two `unsigned char[]` tables and never
appears as a contiguous printable run in the binary, so
`strings chall | grep nmctf` comes up empty.

The program does, however, leak the flag through a **timing oracle**:

```c
for (i = 0; i < FLAG_LEN; i++) {
    c = argv[1][i];
    for (j = 0; j < (int)(unsigned char)c * SCALE; j++) {
        dummy = (dummy * 31 + j) ^ (dummy >> 7);
    }
    if (c != flag[i]) return 0;          // early exit on mismatch
}
if (argv[1][FLAG_LEN] != '\0') return 0;
puts("correct");
```

Two things make the oracle clean:

1. The work at position `i` is `argv[1][i] * SCALE` — so a probe string
   that is *correct* for the first `k` characters runs the loop `k`
   full times.
2. The program exits early on the first mismatch, so the total time
   equals the cumulative work up to (and including) the first mismatch.

That means: with a full-length candidate, the only character that keeps
the program running past position `k` is the correct one.  Time it
carefully and you have a yes/no per position, which is enough to
recover the whole flag.

## Quick recon

```
$ file chall
chall: ELF 32-bit LSB executable, Intel 386 …
$ strings chall | grep nmctf
$
$ objdump -d chall | awk '/<main>:/,/^$/' | grep -c 'mov '
1779
$ objdump -d chall | awk '/<main>:/,/^$/' | grep -E 'j(mp|e|ne)' | wc -l
0
```

`main` is 1.8k `mov` and not a single `j*`.  Plain reversing this is
an exercise in frustration.

## The oracle in practice

```
$ time ./chall wrong
real    0m0.090s          # exited at position 0

$ time ./chall nmctf{m0v_th3_fl4g_l0rd
real    0m1.51s           # exited at the last (no '}') comparison

$ time ./chall nmctf{m0v_th3_fl4g_l0rd}
real    0m1.67s           # correct
```

So the time roughly tracks `sum(argv[1][i])`.  Because ASCII is
roughly the same magnitude per char, the time mostly tracks the
*length of the matched prefix*.

## The attack

The flag is `nmctf{...}` (24 chars in this build).  We know positions
`0..5` (`nmctf{`) and position `23` (`}`), so we only need to recover
positions 6..22.

For a target position `k`, build a 24-char string with:

* positions 0..k-1  = recovered prefix
* position k        = candidate character
* positions k+1..23 = a high-value "tail" of `'z'`

The candidate that produces the **longest** time is the right one,
because only the correct character lets the program keep running and
process the entire `'z'…'z'` tail.

A compact loop of the algorithm:

```python
for pos in range(len(prefix), flag_len - 1):
    best, best_t = '?', -1
    for c in alphabet:                       # e.g. a-z, 0-9, _
        guess = recovered + c + tail
        t = time_run('./chall', guess)
        if t > best_t: best, best_t = c, t
    recovered += best
    tail = tail[1:]                            # shrink the tail
```

With a `SCALE = 300` and a 37-char alphabet, the per-position margin
between right and wrong is ~80–250 ms, well above the run-to-run
jitter (~10–20 ms) on a quiet box.  The whole flag falls out in
~6 minutes on a single core; double the alphabet and it goes to
~10 minutes.

```
[+] pos= 6  best='m'  t=0.663s  margin=+0.570s
[+] pos= 7  best='0'  t=0.703s  margin=+0.609s
…
[+] pos=22  best='d'  t=1.758s  margin=+1.664s
[*] Candidate: nmctf{m0v_th3_fl4g_l0rd}
[*] Verifying:
    stdout : 'correct\n'
[+] FLAG VERIFIED
```

## Why this is a side-channel challenge, not "just guess it"

A few standard trivial-solve vectors are explicitly closed:

* `strings` finds nothing — the flag is split across `BASE[]`/`ADD[]`
  and only reconstructed at runtime (`(BASE[i] + ADD[i]) & 0xff`).
* `objdump -s -j .rodata` shows two non-printable byte runs, neither
  of which spells the flag.
* `gdb` will obviously show `nmctf{…}` on the stack once `main` is
  mid-loop, but that's the debugger escape hatch, not a solve path —
  the rest of the challenge is about the timing oracle.

The defence you'd want to add in a hardened build is a
**constant-time comparison**: don't early-exit on the first mismatch.
A textbook way to do that here is to AND the diffs of all 24
characters and only branch on the final accumulator — that turns the
whole-flag comparison into a single branch and removes the per-position
oracle.  We deliberately left the naive early-exit in so the side
channel is exploitable.

## Reference solver

`solve.py` is the script used to validate this writeup.  Highlights:

```sh
$ python3 solve.py --alphabet 'abcdefghijklmnopqrstuvwxyz0123456789_'
```

Tweak the alphabet to taste; the default 37-char set is what the flag
in this build happens to use.  Adding `--samples 3` reduces noise at
the cost of a ~3x runtime increase; the binary is single-threaded so
it parallelises trivially across cores if you want to be aggressive.
