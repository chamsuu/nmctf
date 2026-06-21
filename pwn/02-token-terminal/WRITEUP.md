# Token Terminal — Integer Overflow, Heap Corruption, Function Pointer Overwrite

this challenge gives us a 32-bit x86 binary that manages a point-of-sale terminal. customers place orders, delete records, claim refunds, and print receipts. at first glance it looks like a standard heap pwnable. the security properties are favorable:

```
Arch: i386-32
RELRO: Partial RELRO
Stack: No canary found
NX:    NX enabled
PIE:   No PIE (0x08048000)
```

no PIE means all the BSS addresses are static. no canary means stack overflows are easy, though we won't need one here. the real bug is subtler.

we fire up the binary locally and start playing with the menu. option 2 — "Process order" — catches our eye. it asks for a quantity as a 2-byte (uint16) value, and then does this:

```c
void cmd_process_order(int sockfd) {
    uint16_t quantity = 0;
    recv(sockfd, &quantity, 2, 0);

    uint16_t alloc_size = (uint16_t)((uint32_t)quantity * 40u);
    void *orders = malloc((size_t)alloc_size);

    recv(sockfd, (char*)orders, quantity * 40u, 0);
    free(orders);
}
```

the allocation size is computed as `(uint16_t)(quantity * 40)`, but the receive uses `quantity * 40` as a full 32-bit product. if the multiplication overflows 16 bits, `alloc_size` truncates to something tiny but the `recv` still expects the full product worth of data. integer overflow into heap overflow.

we pull out a calculator:

```
0x199A * 40 = 0x40010  →  truncated to uint16_t = 0x0010 = 16
```

so `malloc(16)` gets called, but the receive loop will accept up to `0x199A * 40 = 262,160` bytes. that's a massive heap overflow off a 16-byte allocation. the only catch is the server caps the recv at 44 bytes received — which is exactly enough for our overwrite. not a problem.

the next question: what sits after our 16-byte allocation on the heap? we reverse the connection setup function and find deliberate grooming:

```c
void handle_connection(int sockfd) {
    g_pholder = malloc(16);              // 0x20 chunk → placeholder
    g_record  = malloc(sizeof(record_t)); // 0x28 chunk → record, right after

    g_record->item_id = 1;
    g_record->price   = 500;
    g_record->name    = malloc(24);      // separate allocation for name string

    free(g_pholder);  // placeholder goes to tcache[0x20]
}
```

the placeholder (a 16-byte allocation that lives in a 0x20-sized chunk) is freed before the menu loop starts. it sits in tcache's 0x20 bin. when our `malloc(16)` runs during process_order, tcache's LIFO gives us back the placeholder — and the record chunk is immediately adjacent, just like the setup intended.

now we reverse the `record_t` struct from Ghidra:

```
offset 0x00: item_id   (uint32)
offset 0x04: price     (uint32)
offset 0x08: *name     (char pointer)  ← our corruption target
offset 0x0C: desc[16]  (char buffer)
```

from the start of the placeholder's user data, the record's `name` pointer is at offset `+0x28` (24 bytes of placeholder user data + 8 bytes of chunk header + 8 bytes of item_id/price = 40 bytes = 0x28). if we overflow from the placeholder, we can write a controlled value into `record->name`.

so where do we point `name`? the binary has a global struct in BSS:

```c
struct {
    uint32_t  reuse_tag;          // +0x00
    uint32_t  reuse_size;         // +0x04
    char      template[4];        // +0x08  ← point record->name here
    void    (*dispatch)(char *);  // +0x0C  ← our real target
    uint32_t  receipt_id;         // +0x10
} g_state;
```

the plan: overflow `record->name` to point at `g_state.template` at `+0x08`. then, through the delete/refund logic, get an arbitrary write into the `dispatch` function pointer at `+0x0C`.

here's where the challenge gets clever. the delete handler (`cmd_delete_record`) checks if the pointer looks like it's in the BSS region:

```c
uint32_t addr = (uint32_t)g_record->name;
if (addr >= 0x08040000 && addr < 0x08050000) {
    g_corrupted = g_record->name;  // stash it, don't free it
}
```

if the pointer looks like BSS, the delete handler saves it in `g_corrupted` instead of freeing it. then the refund handler (`cmd_claim_refund`) has a special path in `safe_alloc`:

```c
if (n == 16 && g_corrupted) {
    void *p = g_corrupted;
    g_corrupted = NULL;
    return p;          // returns our stashed BSS pointer!
}
```

so the chain works like this:

1. **Set metadata** (menu 1): we send `reuse_tag=0` and `reuse_size=0x21`. these just need to match what the delete logic expects — they're not actual heap metadata, just application-level flags.

2. **Overflow** (menu 2): reclaim the placeholder chunk with `malloc(16)`, send our 44-byte overflow. we overwrite the adjacent record's chunk header (set `size = 0x29`, which is `0x28 | PREV_INUSE` — this keeps the allocator happy if it ever inspects the chunk), and then write `&g_state.template` into `record->name`.

3. **Delete record** (menu 3): the BSS region check fires, `g_corrupted` now holds `&g_state.template`.

4. **Claim refund** (menu 4): `safe_alloc(16)` returns `g_corrupted` — a pointer into BSS. we write a 4-byte tag followed by `&sys_maintenance`. the tag lands in `template[4]` and the address lands on `dispatch`.

5. **Print receipt** (menu 5): calls `g_state.dispatch(g_state.template)`, which triggers `sys_maintenance()` → `system("cat /flag.txt")`.

one detail that tripped us up: the chunk size in the overflow needs to be `0x29`, not `0x21`. we originally used `0x21` because we were thinking in terms of the placeholder's chunk size, but the record chunk is `sizeof(record_t) = 28` bytes, which rounds to a `0x28` chunk with `PREV_INUSE` set → `0x29`. writing `0x21` makes the chunk look smaller than it is and confuses the allocator during later operations. this took a while to trace through — the exploit would work sometimes and crash other times until we aligned the fake chunk size with reality.

the challenge teaches a nice chain: integer overflow to get on the heap, careful grooming to control adjacency, and application-level logic (the delete/refund stash mechanism) to convert a corrupted pointer into an arbitrary write. no libc leak needed — everything lives in the binary's fixed addresses.
