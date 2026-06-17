#!/bin/sh
docker build -t secure-archive . && docker run -p 8080:8000 secure-archive
