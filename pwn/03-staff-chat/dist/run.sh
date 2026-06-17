#!/usr/bin/env bash

chmod +x ./chat ./ld-linux-x86-64.so.2
./ld-linux-x86-64.so.2 --library-path . ./chat