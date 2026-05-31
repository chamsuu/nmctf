#!/bin/bash
# ============================================================
#  Algerian Devs — SSH Bastion Shell Enforcer
# ============================================================

# Strictly block any automated command execution
if [ -n "$SSH_ORIGINAL_COMMAND" ]; then
    echo "Interactive session required. Direct command execution is disabled."
    exit 1
fi

# Force fully interactive bash login shell
exec /bin/bash --login
