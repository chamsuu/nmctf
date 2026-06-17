#!/usr/bin/env python3
"""
Side-channel solver for the M/o/Vfuscator timing-oracle challenge.

The challenge binary takes a candidate string and, for every position i:
  1. Performs argv[1][i] * SCALE units of dummy work.
  2. Compares argv[1][i] to FLAG[i] and exits early on mismatch.

The flag format is `nmctf{...}` and the closing brace is assumed
(only positions 6..L-2 need to be brute-forced).

For each candidate character at position k, we send a string of full
flag length L with:
  - positions 0..k-1  : the recovered prefix
  - position k        : the candidate character
  - positions k+1..L-1: a high-value "tail" (e.g. 'z')
The candidate that produces the LONGEST time is the right one,
because the program only continues past position k (and does the
work for every tail character) if argv[1][k] matched FLAG[k].

Usage:  ./solve.py [--bin ./chall] [--len 24] [--samples 1] [--alphabet ...]
"""

from __future__ import annotations

import argparse
import string
import subprocess
import sys
import time


def time_run(bin_path: str, candidate: str) -> float:
    """Run the binary with `candidate` and return wall-clock seconds."""
    start = time.perf_counter()
    subprocess.run(
        [bin_path, candidate],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return time.perf_counter() - start


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default="./chall", help="path to the challenge binary")
    ap.add_argument("--len", type=int, default=24, help="flag length (default 24)")
    ap.add_argument(
        "--samples",
        type=int,
        default=1,
        help="number of timing samples per candidate (default 1)",
    )
    ap.add_argument(
        "--alphabet",
        default=string.ascii_letters + string.digits + "_-+=./:;,[]{}!@#$%^&*()`~",
        help="candidate characters",
    )
    ap.add_argument(
        "--tail", default="z", help="high-value tail character (default 'z')"
    )
    ap.add_argument(
        "--prefix", default="nmctf{", help="known flag prefix (default 'nmctf{')"
    )
    ap.add_argument(
        "--suffix", default="}", help="known flag suffix (default '}')"
    )
    args = ap.parse_args()

    bin_path = args.bin
    flag_len = args.len
    samples = max(1, args.samples)
    alphabet = "".join(sorted(set(args.alphabet)))
    tail_char = args.tail
    prefix = args.prefix
    suffix = args.suffix

    if len(prefix) + len(suffix) >= flag_len:
        print("[-] prefix+suffix longer than flag", file=sys.stderr)
        return 1

    print(f"[*] binary  : {bin_path}")
    print(f"[*] length  : {flag_len}")
    print(f"[*] alphabet: {alphabet}  ({len(alphabet)} chars)")
    print(f"[*] tail    : {tail_char!r}")
    print(f"[*] samples : {samples}")
    print()

    # Calibrate: time a "definitely-wrong" full-length probe so we
    # know the baseline of a wrong guess at the very first position.
    junk = tail_char * flag_len
    t_junk = min(time_run(bin_path, junk) for _ in range(samples))
    print(f"[*] baseline (all-{tail_char!r}): {t_junk:.3f}s")
    print()

    # Per-position brute force over the unknown region.
    recovered = prefix
    tail = tail_char * (flag_len - len(prefix) - len(suffix))

    for pos in range(len(prefix), flag_len - len(suffix)):
        best_c = "?"
        best_t = -1.0
        for c in alphabet:
            guess = recovered + c + tail
            if len(guess) != flag_len:
                guess = (guess + tail_char * flag_len)[:flag_len]
            t = min(time_run(bin_path, guess) for _ in range(samples))
            if t > best_t:
                best_t = t
                best_c = c
        recovered = recovered + best_c
        tail = tail[1:] if tail else ""
        margin = best_t - t_junk
        print(
            f"[+] pos={pos:>2}  best={best_c!r}  t={best_t:.3f}s  "
            f"margin={margin:+.3f}s  recovered='{recovered}...'"
        )
        sys.stdout.flush()

    recovered = recovered + suffix
    print()
    print(f"[*] Candidate: {recovered}")
    print("[*] Verifying:")
    rc = subprocess.run(
        [bin_path, recovered], capture_output=True, text=True, check=False
    )
    print(f"    stdout : {rc.stdout!r}")
    print(f"    return : {rc.returncode}")
    if rc.stdout.strip() == "correct":
        print("[+] FLAG VERIFIED")
        print(recovered)
        return 0
    print("[-] verification failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
