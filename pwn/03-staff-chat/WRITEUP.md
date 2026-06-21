# Staff Chat — Use-After-Free, XOR Obfuscation, Tcache Poisoning

this challenge is an x86-64 messaging app running against glibc 2.31, and it comes with all the mitigations turned on:

```
Arch: amd64-64
RELRO: Full RELRO
Stack: Canary found
NX:    NX enabled
PIE:   PIE enabled
```

full RELRO means we can't overwrite GOT entries. PIE means we need a leak before we can target any functions. stack canary rules out simple buffer overflows. so we're in heap exploitation territory.

the binary is a simple chat system. you can create messages (malloc), view them, edit them, archive them (free), and list them. the first thing we notice is that `cmd_view_message` and `cmd_edit_message` don't check the `archived` flag before accessing the data pointer. `cmd_archive_message` calls `free(m->data)` and sets `archived = 1`, but leaves the pointer in the slot and the data_size intact. view and edit will happily read from and write to freed memory. clean use-after-free.

but there's a twist. the archive function doesn't just free and leave — it applies a custom "protection" to the freed data:

```c
void cmd_archive_message(int idx) {
    msg_t *m = &g_messages[idx];
    free(m->data);
    *(uint64_t *)(m->data) ^= compute_key(m);  // XOR obfuscation
    m->archived = 1;
}
```

the XOR key is derived from the chunk's size:

```c
static uint64_t compute_key(const msg_t *m) {
    size_t chunk_sz = ((m->data_size + 0x10 + 0x0f) & ~(size_t)0x0f) | 1;
    return (uint64_t)chunk_sz ^ 0x4141414141414141ULL;
}
```

so after `free()`, the first qword of the chunk (which, for an unsorted bin chunk, would be the `fd` pointer) gets XORed with a key we can calculate. since we know `data_size`, we know the key. XORing again reverses it.

our first plan: allocate a large chunk (> 0x408, above the tcache maximum), free it to send it to the unsorted bin, read it via the UAF, XOR the fd pointer to recover `main_arena + 96`, and compute libc base. this works — the leak comes through clean. libc base acquired.

then we call `malloc()` again and the program crashes. hard.

here's where we got stuck for an hour. when glibc puts a chunk in the unsorted bin, it sets both `fd` and `bk` to `main_arena + 96`. the archive function XORs only the first 8 bytes — that corrupts `fd`. `bk` at offset +8 stays clean. the unsorted bin is a doubly-linked list, and when `malloc` scans it on the next allocation, it follows `fd` to the next chunk. our `fd` is XOR-mangled, so it chases a garbage pointer and segfaults.

the fix is simple once you see it: after leaking, use the `edit` UAF to write the *original* (un-XORed) `fd` value back into both `fd` and `bk` slots:

```python
edit(p, 0, LSIZE, p64(main_arena_96) * 2)
```

this repairs the unsorted bin — both pointers now point to `main_arena + 96`, which is what glibc expects for the only chunk in the bin. the next `malloc` that scans the unsorted bin finds a valid list and doesn't crash. this step is easy to miss if you're not thinking about the doubly-linked list invariants.

with libc leaked and the heap repaired, we move to tcache poisoning. we allocate two 0x60-sized chunks (below the 0x408 tcache ceiling), free both to populate the tcache bin, then use the UAF write to overwrite the second chunk's `fd` with `__free_hook`:

```
tcache bin: chunk_B → chunk_C → NULL
after edit: chunk_B → __free_hook → ?
```

two allocations later, the second one returns a pointer to `__free_hook`. we write `system` into it. now any `free()` call triggers our hook.

the trigger path is clean: allocate a new message containing `"/bin/sh\x00"`, then archive it. `cmd_archive_message` calls `free("/bin/sh")`, which hits `__free_hook`, which calls `system("/bin/sh")`. we get a shell.

a few details worth calling out. the XOR reversal math is straightforward but easy to get wrong if you don't pay attention to alignment. glibc's chunk size is always rounded up to the next 16-byte boundary, and the `| 1` sets the `PREV_INUSE` bit on the chunk header. so for a 0x420-byte user allocation, the chunk size calculation goes:

```
data_size = 0x420
chunk_sz  = ((0x420 + 0x10 + 0x0F) & ~0x0F) | 1
          = ((0x430 + 0x0F) & ~0x0F) | 1
          = (0x43F & ~0xF) | 1
          = 0x430 | 1
          = 0x431
xor_key   = 0x431 ^ 0x4141414141414141
          = 0x414141414545730  (truncated to 64 bits)
```

the chunk size computation function in the binary (`compute_key`) exactly mirrors this. we compute the same key on our side, XOR the leaked `fd` value, and out comes `main_arena + 96`. the offset from `main_arena + 96` to libc base is a fixed value from the provided libc — in this case `0x1ecbe0` for glibc 2.31.

for the tcache poisoning, we chose chunk size `0x60` deliberately. it's under the 0x408 tcache threshold (so the chunks stay in tcache, never touching the unsorted bin we just repaired), and it's big enough to hold a pointer plus our dummy data. on glibc 2.31, tcache has no integrity checks on the `fd` pointer — no safe-linking, no pointer mangling. you write whatever address you want and the next allocation returns it. newer glibc versions add `PROTECT_PTR` mangling (XOR with `address >> 12`), but 2.31 is wide open.

we tried the exploit with a 0x50-size chunk at first and it worked fine — the exact size doesn't matter as long as both chunks are the same size (so they share a tcache bin). we settled on 0x60 because it gives a bit more room and the tcache count is generous enough that two frees won't trigger consolidation.

the XOR puzzle is what makes this challenge stick in memory. it's not enough to spot the UAF — you have to understand *why* the unsorted bin breaks after the XOR and how to fix it. the "aha" moment came when we printed both qwords of the leaked chunk and realized only the first was garbled. the second was a clean `main_arena + 96`. that's when we knew the fix was just writing the clean value back over the corrupted one.
