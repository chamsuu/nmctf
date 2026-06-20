#!/usr/local/bin/python3
import sys

inp = input('jail2 > ')

sys.stdout.close()

flag = open('flag.txt').read()

try:
    eval(inp, {'__builtins__': {}})
except SystemExit:
    pass
