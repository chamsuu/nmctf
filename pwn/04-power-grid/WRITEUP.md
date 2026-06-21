# Power Grid — AArch64 Stack Overflow, Custom Canary, Stack Pivot

this one drops us a stripped AArch64 PIE binary that speaks a custom binary protocol. the service manages a power grid controller — you send packets with command bytes and length headers, and the server processes them. we fire up QEMU and start probing.

the protocol is straightforward: a 2-byte little-endian length prefix, then the packet body. body has a command byte at offset 0, a checksum at offset 1, a 2-byte data length at offset 2, and payload at offset 4. the checksum uses a rolling XOR with rotation — reversible but annoying to compute by hand. luckily the solver handles it.

we start poking around with different command bytes. most return "[PLC] Command processed." but command `0x02` loads config data into a global buffer, and command `0xFF` (with a bad checksum) triggers a diagnostic dump:

```
[EMERG] SP=0xFFFFF6E7F4F0 TICK=0 PID=42 CODE=0xAAAA00000B20
```

this is a goldmine. it leaks the stack pointer, process ID, a tick counter, and — most importantly — the runtime address of `plc_emergency_dump`. since PIE is on, every address in the binary slides by a random base. but we now have one known runtime address, and we know its file offset (0x0B20). subtract to get the PIE base, then add offsets to find gadgets, BSS, and PLT stubs.

the vulnerability is in the generic command handler, `handle_command`. it allocates a frame on the stack:

```c
void handle_command(int out_fd, const uint8_t *packet, size_t pkt_len) {
    volatile command_frame_t frame;
    // ...
    memcpy((void *)frame.cmd_buf, packet + 4, copy_len);
}
```

`copy_len` comes from the packet header (`pkt_len - 4`) and is never checked against the buffer size. `cmd_buf` is 128 bytes but the attacker controls the copy length entirely. the frame after the buffer contains:

```c
typedef struct {
    char     cmd_buf[128];
    uint64_t canary;               // custom, NOT the stack guard
    void   (*pivot)(uint64_t *);   // function pointer
    uint64_t *pivot_arg;           // argument to pivot()
} command_frame_t;
```

so we can overflow `cmd_buf`, overwrite the canary, then overwrite a function pointer and its argument. but the binary validates the canary before calling the pivot:

```c
if (frame.canary != generate_canary(sp_context)) {
    write(STDERR_FILENO, "[PLC] Stack corruption!\n", 24);
    _exit(1);
}
```

this looks scary until we reverse `generate_canary`. it's not a random cookie — it's computed from values we already have:

```c
static uint64_t generate_canary(uint64_t sp_context) {
    uint64_t raw = g_tick ^ (uint64_t)getpid() ^ sp_context ^ 0xDEADBEEFULL;
    return raw * 0x1337133713371337ULL;
}
```

`g_tick`, `getpid()`, and `sp_context` (the stack pointer) are all in the diagnostic leak. we can compute the exact canary ourselves. one subtlety: `g_tick` increments during normal command processing. if we send the config command first (which bumps `g_tick` once), the canary at overflow time uses `tick + 1`. miss this and the canary check fails and the process exits silently.

on AArch64, the first eight arguments go in registers `x0` through `x7`. the pivot function pointer gets called with `pivot_arg` in `x0`. we need a gadget that does something useful with `x0`. luckily, the binary has a purpose-built gadget right there:

```c
__attribute__((noinline, noreturn))
void stack_pivot(uint64_t *chain) {
    asm volatile(
        "mov sp, x0\n"           // SP = pivot_arg (our controlled address)
        "ldp x29, x30, [sp], #16\n"  // pop frame ptr and return addr
        "ldp x0, x1, [sp], #16\n"    // pop first two args
        "ret\n"
    );
}
```

this moves our controlled `pivot_arg` into the stack pointer, then pops a frame pointer (`x29`), return address (`x30`), and two arguments (`x0`, `x1`) from the new stack location. it's almost too perfect — the challenge author left us the exact gadget we need.

our first attempt pointed the pivot at a short ROP chain placed at the start of the 8KB BSS buffer `g_command_buf`. the chain set `x0` to the address of `"/bin/sh"` and returned to `system@plt`. it crashed with a segfault somewhere deep inside `do_system`.

after some staring at the disassembly, we realized: `system()` on AArch64 internally calls `fork()` and `execve()`, and both of those need several KB of stack space for their local frames. our pivot had placed `SP` at the bottom of the BSS buffer, and when `system()` tried to grow the stack downward, it walked right off the end of the mapped page. segfault.

the fix is to place the ROP chain near the *end* of the 8KB BSS buffer. we use the config command (`0x02`) to write our chain at offset `0x1E00` (7680 bytes into the 8192-byte buffer), leaving about 7.5KB of clean space below the pivot point for `system()` to use. the chain itself is just four qwords:

```python
chain = p64(0) + p64(system) + p64(cmd_addr) + p64(0)
#        x29=0    x30=ret addr    x0=argv       x1=0
```

when the pivot gadget executes `ret`, `x30` holds `system@plt` and `x0` holds the address of `"cat /flag.txt"` (also staged in BSS, just past the chain). we get a shell.

the overflow payload itself fills the 128-byte `cmd_buf`, then writes the computed canary, then `&stack_pivot`, then `&chain_in_bss`. the forward-write nature of the overflow means we don't need to worry about trashing the return address or frame pointer — the pivot replaces all of that with our controlled values from BSS.

this challenge does a nice job of teaching AArch64 exploitation fundamentals: use a code pointer leak to beat PIE/ASLR, reverse a predictable canary (always check if the "protection" is actually random!), chain through a provided pivot gadget, and respect the platform's stack usage for library calls. the "system needs stack space" realization is the kind of thing you only learn by crashing and then actually thinking about what `system()` does internally.
