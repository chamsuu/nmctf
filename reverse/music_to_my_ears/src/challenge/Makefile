CC = gcc
CFLAGS = -O2 -s -fno-stack-protector
TARGET = temporal_vault

all: flag_data.h $(TARGET)
	strip $(TARGET)

flag_data.h:
	python3 build_flag.py

$(TARGET): chall.c flag_data.h
	$(CC) $(CFLAGS) -o $(TARGET) chall.c

clean:
	rm -f $(TARGET) flag_data.h

.PHONY: all clean
