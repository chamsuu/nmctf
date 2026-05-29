#!/usr/bin/env python3
import os
import sys
import random


EPOCH = 624
TARGET = 42
FLAG = os.environ.get("FLAG", "nmCTF{test_flag}")


def build():
    rng = random.Random(0xCAFE)
    state = rng.getstate()
    return state


SAVED = build()
gen = random.Random(0)
gen.setstate(SAVED)
pos = 0


def reset():
    global gen, pos
    gen.setstate(SAVED)
    pos = 0


def read():
    global pos, gen
    if pos >= EPOCH:
        reset()
    v = gen.getrandbits(32)
    pos += 1
    return v


def show_commands():
    print("  SAMPLE             - Take one reading")
    print("  STREAM <count>     - Take multiple readings")
    print("  STATUS             - Show current step counter")
    print("  ADVANCE <count>    - Advance step counter")
    print("  REVEAL             - Retrieve anomaly data")
    print("  HELP               - Show this message")
    print("  EXIT               - Disconnect")
    print()


def main():
    print()
    print("   =============================================")
    print("     CHRONOS v1.2 — Sequential Data Analyzer")
    print("     University Computer Lab, 1984")
    print("   =============================================")
    print()
    print("  This terminal runs the CHRONOS analyzer.")
    print("  The computation cycle repeats every 624 steps.")
    print("  Dr. Eleanor's notes mention an anomaly")
    print("  pattern that appears precisely at step 42.")
    print()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
        except EOFError:
            break

        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "SAMPLE":
            v = read()
            print(f"  {v}")

        elif cmd == "STREAM":
            if len(parts) > 1:
                try:
                    count = int(parts[1])
                except ValueError:
                    print("  Invalid count.")
                    continue
            else:
                count = 10
            if count > EPOCH:
                count = EPOCH
            out = []
            for _ in range(count):
                out.append(f"  {read()}")
            print("\n".join(out))

        elif cmd == "STATUS":
            if pos == 0:
                print(f"  CHRONOS at step 0.")
            else:
                print(f"  CHRONOS at step {pos} of {EPOCH}.")

        elif cmd == "ADVANCE":
            if len(parts) > 1:
                try:
                    count = int(parts[1])
                except ValueError:
                    print("  Invalid count.")
                    continue
            else:
                count = 1
            for _ in range(count):
                read()
            print(f"  Advanced {count} step(s).")

        elif cmd == "REVEAL":
            if pos % EPOCH == TARGET:
                print(f"  [ANOMALY DETECTED] {FLAG}")
            else:
                print(f"  No anomaly at current step.")

        elif cmd == "HELP":
            show_commands()

        elif cmd == "EXIT":
            break

        else:
            print(f"  Unknown command: {cmd}")

        sys.stdout.flush()


if __name__ == "__main__":
    main()
