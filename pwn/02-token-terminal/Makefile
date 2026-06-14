CC     = gcc
CFLAGS = -m32 -O1 -fno-pie -no-pie -fno-stack-protector \
         -Wl,-z,noexecstack -Wl,-z,relro

.PHONY: all clean dist verify

all: build/pos

build/pos: src/pos.c
	$(CC) $(CFLAGS) -o $@ $<
	cp $@ dist/pos
	strip dist/pos

verify: build/pos
	@echo "[*] Security properties:"
	checksec --file=build/pos
	@echo "[*] BSS receipt structure address:"
	nm build/pos | grep g_receipt
	@echo "[*] system@PLT address:"
	objdump -d build/pos | grep -A3 "<system@plt>"

clean:
	rm -f build/pos dist/pos