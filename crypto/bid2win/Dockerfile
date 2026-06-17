FROM python:3-slim

RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/server.py .
COPY flag.txt .

RUN useradd -m ctf && chown -R ctf:ctf /app
USER ctf

EXPOSE 1337

CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:python3 /app/server.py,pty,raw,echo=0"]
