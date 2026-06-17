CC_A64  = aarch64-linux-gnu-gcc
CFLAGS  = -O2 -fPIE -fno-stack-protector \
          -march=armv8-a -fno-omit-frame-pointer
LDFLAGS = -pie -Wl,-z,relro,-z,now

.PHONY: all clean dist verify

all: build/plc

build/plc: src/plc.c
	mkdir -p build dist
	$(CC_A64) $(CFLAGS) $(LDFLAGS) -o $@ $<
	cp $@ dist/plc
	aarch64-linux-gnu-strip dist/plc

verify: build/plc
	checksec --file=build/plc
	@echo "[*] Checking for pivot gadget..."
	aarch64-linux-gnu-objdump -d build/plc --disassemble=stack_pivot
	@echo "[*] PIE offsets used by the solver:"
	@echo "[*] plc_emergency_dump:"
	aarch64-linux-gnu-nm build/plc | grep " plc_emergency_dump$$"
	@echo "[*] g_command_buf:"
	aarch64-linux-gnu-nm build/plc | grep g_command_buf
	@echo "[*] stack_pivot:"
	aarch64-linux-gnu-nm build/plc | grep " stack_pivot$$"
	@echo "[*] system@plt:"
	aarch64-linux-gnu-objdump -d build/plc | grep "<system@plt>"

clean:
	rm -f build/plc dist/plc
