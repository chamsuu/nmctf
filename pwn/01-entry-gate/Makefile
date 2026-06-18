CC_ARM   = arm-linux-gnueabihf-gcc
CFLAGS   = -O1 -march=armv7-a -mfpu=vfpv3 -mfloat-abi=hard -marm -mthumb-interwork \
           -fno-pie -no-pie -fno-stack-protector \
           -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
           -Wl,-z,noexecstack -static

CFLAGS_THUMB = -O1 -march=armv7-a -mfpu=vfpv3 -mfloat-abi=hard -mthumb -mthumb-interwork \
               -fno-pie -no-pie -fno-stack-protector \
               -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0

.PHONY: all clean dist verify

all: build/doorbell

build/validate_thumb.o: src/validate.c
	$(CC_ARM) $(CFLAGS_THUMB) -c -o $@ $<

build/doorbell: src/doorbell.c build/validate_thumb.o
	$(CC_ARM) $(CFLAGS) -o $@ $^
	cp $@ dist/doorbell
	arm-linux-gnueabihf-strip dist/doorbell

verify: build/doorbell
	@echo "[*] Checking gadgets..."
	ROPgadget --binary build/doorbell --only "pop" | grep "pop {r0, r4, pc}"
	@echo "[*] Checking unlock_door address..."
	arm-linux-gnueabihf-nm build/doorbell | grep unlock_door

clean:
	rm -f build/* dist/doorbell