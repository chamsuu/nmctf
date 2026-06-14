FROM ubuntu:22.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        qemu-user-static \
        libgcc-s1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/sh ctf

COPY build/doorbell /challenge/doorbell
COPY flag.txt /flag.txt
RUN chmod 444 /flag.txt && \
    chmod 755 /challenge/doorbell

EXPOSE 1337

# Force rebuild by changing comment
CMD ["qemu-arm-static", "/challenge/doorbell"]