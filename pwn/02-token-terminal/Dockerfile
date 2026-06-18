FROM ubuntu:18.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        lib32gcc1 \
        libc6-i386 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/sh ctf

COPY dist/pos /challenge/pos
COPY flag.txt /flag.txt

RUN chmod 444 /flag.txt && \
    chmod 755 /challenge/pos

EXPOSE 1337
CMD ["/challenge/pos"]