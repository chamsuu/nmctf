CC     = gcc
CFLAGS = -m32 -O1 -fno-pie -no-pie -fno-stack-protector \
         -Wl,-z,noexecstack -Wl,-z,relro

.PHONY: all clean verify dist

all: build/pos

build/pos: src/pos.c
	$(CC) $(CFLAGS) -o $@ $<

dist: build/pos
	strip build/pos -o dist/pos

verify: build/pos
	@echo "[*] Security properties:"
	checksec --file=build/pos
	@echo "[*] BSS receipt structure address:"
	nm build/pos | grep g_state
	@echo "[*] sys_maintenance address:"
	nm build/pos | grep sys_maintenance

clean:
	rm -f build/pos dist/pos