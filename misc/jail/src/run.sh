#!/bin/bash
docker build -t jail-loop1 .
docker run -d --name jail-loop1-instance -p 1337:1337 jail-loop1
echo "[+] jail-loop1 running on port 1337"