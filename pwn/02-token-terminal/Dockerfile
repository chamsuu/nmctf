# Build stage - compile on Ubuntu 18.04
FROM ubuntu:18.04 AS builder

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        gcc-multilib && \
    rm -rf /var/lib/apt/lists/*

COPY src/pos.c /tmp/pos.c
WORKDIR /tmp

RUN gcc -m32 -O1 -fno-pie -no-pie -fno-stack-protector \
    -Wl,-z,noexecstack -Wl,-z,relro \
    -o pos pos.c

# Runtime stage - run on Ubuntu 18.04
FROM ubuntu:18.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        lib32gcc1 \
        libc6-i386 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/sh ctf

COPY --from=builder /tmp/pos /challenge/pos
COPY flag.txt /flag.txt

RUN chmod 444 /flag.txt && \
    chmod 755 /challenge/pos

EXPOSE 1337
CMD ["/challenge/pos"]