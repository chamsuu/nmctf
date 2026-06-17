#!/usr/bin/python3

# can override something?

inp = ""

def blacklist():
    global inp
    if inp.isascii() == False:
        return True
    bad_cmds = ['"',
                "'",
                "print",
                "_",
                "import",
                "os",
                "lambda", 
                "system",
                ".",
                 'help', 
                "breakpoint",
                "callable",
                "getattr",
                "setattr",
                "globals",
                '108',
                "builtins",
                "input",
                "compile",
                "eval",
                "exec",
                "open",
                "read"
                ]
    for i in bad_cmds:
        if i in inp:
            print("Blacklisted words found")
            return True
    return False

while True:
    inp = input("> ")
    if not blacklist():
        try:
            exec(inp)
        except Exception as e:
            print("snek says: Error!")
            exit(0)
    else:
        print("snek says: Blacklisted!")
        exit(0)
