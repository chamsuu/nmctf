FROM python:3.13-slim

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 ctf

WORKDIR /home/ctf
COPY jail.py flag.txt ./

RUN chmod 555 /home/ctf \
    && chmod 444 /home/ctf/flag.txt \
    && chmod 555 /home/ctf/jail.py

USER ctf

CMD ["socat", "tcp-listen:1337,fork,reuseaddr", "exec:python3 -u jail.py"]