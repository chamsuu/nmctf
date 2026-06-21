# Entry Gate — ARM32 Stack Overflow, ROP

so this challenge drops us an ARM32 binary, which already sets the tone — we're not in x86 land. we fire up `checksec` and immediately get good news:

```
Arch: arm-32
Stack: No canary found
NX:    NX enabled
PIE:   No PIE (0x10000)
```

no PIE, no canary. only NX is on, which means shellcode is out but ROP is wide open. the binary is statically linked and stripped, so we're going to be hunting gadgets by hand.

the service pretends to be a door firmware updater, listening on a TCP socket. it forks for each connection and presents a menu:

```
=== PixelVault Entry System v1.2 ===
[1] Authenticate
[2] Upload firmware update
Choice:
```

we try option 1 first. it asks for an 8-byte PIN and checks `pin[0] == '\x00'`. sending a null byte gets us through, but the handler just says "Access denied" and moves on. option 1 is a decoy — the real action is in option 2.

we poke around the binary in Ghidra and spot the bug almost immediately. the `recv_firmware_payload` function allocates 128 bytes on the stack but tells `recv` it can take 256:

```c
static void __attribute__((noinline)) recv_firmware_payload(int sockfd) {
    char incoming[128];
    recv(sockfd, incoming, 256, 0);  // whoops
}
```

classic. 128 bytes of buffer, 256 bytes of incoming data. that's a clean 128-byte overflow to play with. the function also redirects stdout and stderr to the socket before the vulnerable `recv`, so anything the program prints after the overflow (like the flag from `system()`) goes straight to us.

the target is obvious — there's an `unlock_door` function that prints the flag if you give it the right code:

```c
void unlock_door(unsigned int door_code) {
    if (door_code == 0xC0DEC0DE) {
        puts("[GATE] Access granted.");
        system("cat /flag.txt");
    }
}
```

our first attempt was straightforward: send 132 bytes of padding (128 for the buffer plus 4 for the saved `r4` that ARM32's calling convention pushes onto the stack), then the address of `unlock_door`. we computed the address statically — the binary is at fixed address `0x10000` with no PIE — so we just looked up `unlock_door` at `0x10374`.

we send the payload and... the connection drops. a segfault. no flag, no "Access granted," just a cold dead socket. a lot of players hit this exact wall — they'd overwrite the return address, see the QEMU process crash (`qemu: uncaught target signal 11 (Segmentation fault)`), and assume the exploit was broken. but the crash *is* the right path — it means we successfully hijacked `pc` and arrived at `unlock_door`. the crash happens inside `unlock_door` itself.

we stare at the disassembly and it clicks: ARM32 passes arguments in registers, not on the stack. `r0` holds the first argument. when our overflow jumps directly to `unlock_door`, `r0` still has whatever garbage was left from the previous function's epilogue. the function does `if (door_code == 0xC0DEC0DE)` — fails the check, falls into the `else` branch that calls `system()`. but with garbage in `r0`, `system()` tries to execute a garbage string pointer, and the process segfaults. the segfault isn't a setback — it's confirmation that we landed exactly where we wanted and just need to fix `r0`.

this is where being in a foreign architecture teaches you something. on x86 and x86-64 we're so used to arguments going on the stack that we forget other ABIs exist. ARM32's register-based calling convention means we can't just jump to the target — we need to set up `r0` first. we need a gadget.

we run ROPgadget on the unstripped build binary:

```
$ ROPgadget --binary doorbell --only "pop" | grep "pop {r0, r4, pc}"
0x0001e314 : pop {r0, r4, pc}
```

beautiful. this gadget pops three values off the stack: a value into `r0`, a dummy into `r4` (which we don't care about — it's just a callee-saved register on the stack frame), and an address into `pc`, the program counter. the stack after our overflow shapes up like this:

```
[sp+0x00]  incoming[128]        ← filled with 'A's
[sp+0x80]  saved r4             ← overwritten with 'B's
[sp+0x84]  saved lr (ret addr)  ← gadget: pop {r0, r4, pc}
[sp+0x88]  0xC0DEC0DE           ← popped into r0 (door code)
[sp+0x8C]  0x41414141           ← popped into r4 (don't care)
[sp+0x90]  0x00010374           ← popped into pc (unlock_door)
```

one nice thing about ARM32 static binaries: the gadgets are everywhere. `pop {r0, r4, pc}` is a common epilogue pattern, so we didn't have to chain multiple gadgets or do anything clever with stack pivoting. one gadget, one jump, flag printed.

the full exploit is about 30 lines of Python. no leak needed because there's no PIE. no brute-force because addresses are static. the only real puzzle is the ABI — understanding that arguments go in registers rather than on the stack.

```python
# The core ROP chain in all its simplicity
payload  = b'A' * 128           # fill incoming[] buffer
payload += b'B' * 4             # clobber saved r4
payload += p32(0x1e314)         # pop {r0, r4, pc}
payload += p32(0xC0DEC0DE)      # r0 = magic door code
payload += p32(0x41414141)      # r4 = don't care
payload += p32(0x10374)         # pc → unlock_door
```

one thing we tried early on that didn't work: jumping to `system` directly from the ROP chain with a pointer to `"cat /flag.txt"`. the binary has `system` imported (it's used in `unlock_door`), so the symbol is there. but the flag file path isn't in the binary's string table, and we didn't have a convenient BSS buffer to stage it in. `unlock_door` already hardcodes the right command, so letting it handle the `system` call was simpler. no need to overthink it.

we also briefly worried about Thumb interworking — the binary mixes ARM and Thumb code (there's a `validate_thumb.o` linked in). if the gadget or target had the LSB set (indicating Thumb mode), the CPU would switch instruction sets and our addresses would be off by one. but both the gadget and `unlock_door` are compiled in ARM mode, so the addresses are clean 4-byte-aligned values. no interworking headaches on this one.

it's a warm but instructive opener for the pwn track, and it makes you actually read the ARM disassembly instead of blindly pasting addresses.
