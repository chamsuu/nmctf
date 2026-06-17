FROM ubuntu:22.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        libc6-arm64-cross \
        qemu-user-static \
        socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/sh ctf
COPY dist/plc /challenge/plc
COPY flag.txt  /flag.txt
RUN chmod 444 /flag.txt && chmod 755 /challenge/plc

EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,fork,reuseaddr", \
     "EXEC:timeout 120 qemu-aarch64-static -L /usr/aarch64-linux-gnu /challenge/plc,su-d=ctf,stderr"]
