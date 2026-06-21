# Vault Driver — Kernel Double-Fetch Race, Data-Only Cred Overwrite

this is the capstone kernel challenge, and honestly when we first saw the `vault_sec.ko` kernel module and the QEMU boot script, we felt that jolt of panic that comes with kernel exploitation. wrong crash means a kernel panic. the constraints are brutal. but after getting the environment booted and poking around, it turned out to be one of the most satisfying challenges in the track.

the first thing we do inside the QEMU VM is inventory the environment:

```
/ # cat /proc/version
Linux version 6.18.9 (gcc (GCC) 13.2.0) #1 SMP PREEMPT_DYNAMIC

/ # cat /proc/cpuinfo | grep flags
... smep smap ...

/ # cat /proc/sys/kernel/kptr_restrict
0

/ # lsmod
vault_sec 16384 0 - Live 0xffffffffc0000000 (O)
```

kptr_restrict is zero — that's a huge relief. it means `/proc/kallsyms` and `/sys/module/*/sections/*` are readable and contain real kernel addresses. no information leak exploit needed — the kernel just tells us where everything is. we can read the module base with a simple `fopen("/sys/module/vault_sec/sections/.text", "r")`.

the mitigations are all active: SMEP prevents the kernel from executing userspace code. SMAP prevents the kernel from even *reading* userspace memory in kernel mode (without special instructions). KASLR randomizes the kernel base (but kptr_restrict=0 neuters this for the module). KPTI isolates kernel page tables, so even if we hijack control flow, we can't return to userspace without a trampoline.

the module registers a misc device at `/dev/vault_sec` and a proc file at `/proc/vault_status`. the IOCTL handler in `vault_ioctl` implements a "secure staging" feature — you submit a `struct vault_request` with a `door_id` and `data_len`, and the kernel copies that many bytes into a 256-byte global buffer:

```c
static uint8_t g_vault_staging[256];  // the target buffer
```

the handler uses a seqlock pattern that looks like it's trying to be thread-safe, but actually it's the vulnerability:

```c
static long vault_ioctl(struct file *f, unsigned int cmd, unsigned long arg) {
    struct vault_request __user *ureq = (void __user *)arg;

    // [A] FIRST FETCH: read data_len from userspace and validate
    uint32_t validated_len = 0;
    get_user(validated_len, &ureq->data_len);
    if (validated_len > sizeof(g_vault_staging))   // max 256
        return -EINVAL;

    // [B] RACE WINDOW: deliberate 80-120ms sleep
    usleep_range(80000, 120000);

    // [C] SECOND FETCH: re-read the ENTIRE struct from userspace
    struct vault_request req;
    copy_from_user(&req, ureq, sizeof(req));

    // [D] OVERFLOW: uses req.data_len — which may have changed!
    copy_from_user(g_vault_staging,
                   (uint8_t __user *)arg + sizeof(req), req.data_len);
}
```

the pattern is a classic TOCTOU (time-of-check, time-of-use) double fetch. at **[A]** the kernel reads `data_len` from userspace into a local variable and checks it. at **[B]** it sleeps for up to 100ms — an eternity in CPU time. during that sleep, a racing thread in userspace can change `data_len` from a safe value (like 64) to a malicious value (like `0x4000`). when the kernel wakes up, it re-reads the *entire struct* at **[C]**, getting the attacker's modified `data_len`. then it uses that length at **[D]** to copy way more than 256 bytes into `g_vault_staging`.

100ms is huge for a race window. on a typical CTF VM with a couple cores, the race is trivially winnable — we don't need nanosecond-precise timing or cache-based side channels. a simple pair of threads, one flipping the value and the other calling `ioctl` in a loop, wins within a handful of attempts.

so we have a kernel heap overflow off a BSS buffer. what do we overwrite? SMEP and SMAP make control-flow hijacking unattractive — we'd need a kernel ROP chain, which requires knowing the kernel image base (doable via kallsyms) and finding gadgets (tedious but possible). but there's an easier path: **data-only attack**.

the kernel heap behind `g_vault_staging` contains slab allocations. one of the most common slab objects is `struct cred` — the credential structure that holds each process's effective UID, GID, supplementary groups, and capabilities. in this kernel, `struct cred` is 192 bytes, living in the `kmalloc-192` slab cache. the relevant fields:

```
offset 0x00: usage (atomic_t, 4 bytes)  — kernel refcount; must be ≥ 1
offset 0x04: uid   (kuid_t, 4 bytes)    — real user ID
offset 0x08: gid   (kgid_t, 4 bytes)    — real group ID
offset 0x0C: suid, sgid, euid, egid...  — saved/cached copies
```

if we overwrite `uid` and `gid` to 0 while keeping `usage` at 1, the process becomes root. the `usage` field is critical — glibc/kernel use it for reference counting, and if it drops to 0, the kernel frees the cred struct, causing a use-after-free panic.

but we don't know exactly where the cred structs are relative to `g_vault_staging`. the kernel heap layout depends on allocation order, slab coloring, and random state. so we **spray**: fork hundreds of child processes, each getting its own `struct cred` allocated from `kmalloc-192`. after 512 forks, the heap is densely packed with cred structs near our buffer:

```c
for (int i = 0; i < 512; i++) {
    pid_t pid = fork();
    if (pid == 0) {
        pause();  // child waits for signal
    }
}
```

each child sits in `pause()`, holding its cred struct alive in the heap. now we race: the parent thread toggles `data_len` from 64 to `0x4000` in a timing loop, while the main thread calls `ioctl` repeatedly. each time the race wins, the kernel copies our 16KB payload over the BSS buffer and into the heap beyond.

our payload is a repeating 192-byte pattern:

```c
for (size_t off = 0; off < 0x4000; off += 0xC0) {
    *(uint32_t *)(payload + off + 0x00) = 1;   // usage = 1  (keeps cred alive)
    *(uint32_t *)(payload + off + 0x04) = 0;   // uid   = 0  (root)
    *(uint32_t *)(payload + off + 0x08) = 0;   // gid   = 0  (root)
    // offsets 0x0C through 0xBF are zeroed by memset
}
```

the 192-byte stride means every `kmalloc-192` slot in the overflow path gets its uid/gid zeroed and its usage set to a valid value. most of these slots will be cred structs (thanks to the spray), and a few might be other slab objects — the usage=1 pattern is harmless for those.

after each race attempt, we scan `/proc/<pid>/status` for all the children. when we see:

```
Uid:    0       0       0       0
```

we know that child's cred has been overwritten. we send it `SIGUSR1`, it wakes up from `pause()`, calls `execve("/bin/busybox", "cat", "/flag.txt")` — as root — and prints the flag.

the key insight: we don't need code execution. SMEP and SMAP both protect the CPU's instruction fetch and memory access pipelines, but they don't protect *data*. credentials are just integers in memory. overwrite the right integers and the kernel treats your process as root. it's the same principle as the classic `commit_creds(prepare_kernel_cred(NULL))` but without needing to call any kernel functions — we modify the cred directly via the heap overflow.

this challenge is a solid introduction to kernel exploitation without requiring ROP chains or `ret2usr` trampolines. it teaches the double-fetch pattern, the importance of `/proc` and `/sys` for ASLR bypass in kernel CTFs, the slab allocator's fixed-size bins, and the elegance of data-only attacks when control-flow mitigations are present. the 100ms race window makes it winnable without hardware-specific timing primitives, keeping the difficulty accessible while still feeling like "real" kernel exploitation.
