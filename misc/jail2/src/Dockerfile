FROM python:3.13-slim

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN useradd -m ctf

WORKDIR /app
COPY main.py /app/run
COPY flag.txt /app/flag.txt
RUN chmod 755 /app/run && chmod 444 /app/flag.txt

USER ctf
CMD socat tcp-l:13337,reuseaddr,fork exec:"python3 /app/run",stderr
