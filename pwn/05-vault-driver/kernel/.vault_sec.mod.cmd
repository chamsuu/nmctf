savedcmd_vault_sec.mod := printf '%s\n'   vault_sec.o | awk '!x[$$0]++ { print("./"$$0) }' > vault_sec.mod
