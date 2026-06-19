FROM python:3.12-slim

WORKDIR /challenge
COPY app.py flag.txt ./

RUN useradd -m ctf
USER ctf

EXPOSE 1337
CMD ["python3", "app.py"]
