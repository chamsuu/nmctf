FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends socat && \
    pip install --no-cache-dir pycryptodome && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/server.py .
COPY flag.txt .

RUN useradd -m ctf && chown -R ctf:ctf /app
USER ctf

EXPOSE 1337
CMD ["socat", "-T120", "TCP-LISTEN:4000,reuseaddr,fork", "EXEC:python3 -u /app/server.py"]
