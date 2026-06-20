#!/bin/bash
docker build -t jail2 .
docker run -d --restart=always -p 13337:13337 localhost/jail2
