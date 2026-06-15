FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        socat \
        gcc \
        libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Verify glibc is 2.31 before proceeding
RUN /lib/x86_64-linux-gnu/libc.so.6 --version | head -1
# Must print: GNU C Library (Ubuntu GLIBC 2.31-...)

# Compile inside the container to link against glibc 2.31
COPY src/chat.c /tmp/chat.c
RUN mkdir -p /challenge && \
    gcc -O1 -fPIE -pie -fstack-protector-strong \
    -Wl,-z,relro,-z,now -Wl,-z,noexecstack \
    -o /challenge/chat /tmp/chat.c && \
    rm /tmp/chat.c && \
    strip /challenge/chat

RUN useradd -m -s /bin/sh ctf
COPY flag.txt /flag.txt
RUN chmod 444 /flag.txt && chmod 755 /challenge/chat

EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,fork,reuseaddr", \
     "EXEC:timeout 120 /challenge/chat,su-d=ctf"]