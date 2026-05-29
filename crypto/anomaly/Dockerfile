FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /challenge
COPY flag.txt /flag.txt
COPY dist/chall.py .

EXPOSE 4000
CMD ["socat", "-T60", "TCP-LISTEN:4000,reuseaddr,fork", "EXEC:python3 -u chall.py"]
