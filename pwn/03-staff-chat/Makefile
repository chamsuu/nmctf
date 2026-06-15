CC     = gcc
CFLAGS = -O1 -fPIE -pie -fstack-protector-strong \
         -Wl,-z,relro,-z,now \
         -Wl,-z,noexecstack

.PHONY: all clean dist verify

all: build/chat

build/chat: src/chat.c
	$(CC) $(CFLAGS) -o $@ $<
	cp $@ dist/chat

verify: build/chat
	checksec --file=build/chat

clean:
	rm -f build/chat dist/chat