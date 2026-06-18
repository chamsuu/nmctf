FROM ubuntu:22.04

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        qemu-system-x86 \
        socat \
        kmod && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m ctf

# Copy binaries - these must be pre-built
COPY dist /challenge/dist
COPY qemu/run.sh /challenge/run.sh
COPY flag.txt /flag.txt
RUN chmod +x /challenge/run.sh

EXPOSE 1337

CMD ["socat", \
     "TCP-LISTEN:1337,fork,reuseaddr", \
     "EXEC:/challenge/run.sh"]