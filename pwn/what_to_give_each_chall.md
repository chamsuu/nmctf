Player Distribution Files

Challenge 01: Entry Gate Firmware (ARM32)

dist/
├── doorbell          # ARM32 binary (stripped)
├── run.sh            # Local launcher
└── README.md         # Connection info

Challenge 02: Token Exchange Terminal (x86_32)

dist/
├── pos               # x86_32 binary (stripped)
├── libc.so.6         # glibc 2.27
├── ld-linux.so.2     # 32-bit linker
├── run.sh            # Local launcher
└── README.md         # Connection info

Challenge 03: Staff Chat Module (x86_64)

dist/
├── chat              # x86_64 binary (stripped)
├── libc.so.6         # glibc 2.31
├── ld-linux-x86-64.so.2
├── run.sh            # Local launcher
└── README.md         # Connection info

Challenge 04: Arcade Power Grid Controller (ARM64)

dist/
├── plc               # ARM64 binary (stripped)
├── run.sh            # Local launcher
└── README.md         # Connection info

Challenge 05: Security Vault Driver (Kernel)

dist/
├── bzImage           # Pre-built kernel 5.15
├── rootfs.cpio.gz    # Root filesystem
├── vault_sec.ko       # Kernel module
├── System.map         # Kernel symbols
├── run.sh            # QEMU launcher
└── README.md         # Connection info

─────────────────────────────────────────────────────────────────────────────────

Summary

┌───────────────────────────────────────────────────────────────────────────────┐
│ Challenge: 01 ARM32                                                           │
│ Binary: ✅                                                                    │
│ Libc: ❌                                                                      │
│ Linker: ❌                                                                    │
│ Kernel Files: ❌                                                              │
│ Launcher: ✅                                                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ Challenge: 02 x86_32                                                          │
│ Binary: ✅                                                                    │
│ Libc: ✅                                                                      │
│ Linker: ✅                                                                    │
│ Kernel Files: ❌                                                              │
│ Launcher: ✅                                                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ Challenge: 03 x86_64                                                          │
│ Binary: ✅                                                                    │
│ Libc: ✅                                                                      │
│ Linker: ✅                                                                    │
│ Kernel Files: ❌                                                              │
│ Launcher: ✅                                                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ Challenge: 04 ARM64                                                           │
│ Binary: ✅                                                                    │
│ Libc: ❌                                                                      │
│ Linker: ❌                                                                    │
│ Kernel Files: ❌                                                              │
│ Launcher: ✅                                                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ Challenge: 05 Kernel                                                          │
│ Binary: ✅                                                                    │
│ Libc: ❌                                                                      │
│ Linker: ❌                                                                    │
│ Kernel Files: ✅                                                              │
│ Launcher: ✅                                                                  │
└───────────────────────────────────────────────────────────────────────────────┘

Notes:

  • ARM challenges don't include libc (static or irrelevant)
  • x86 challenges include matching libc + linker
  • Kernel challenge includes full boot files
  • All include stripped binaries and run scripts
  • README.md only has connection info (minimal descriptions)
