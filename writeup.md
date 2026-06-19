# Operation Numidian - Official Writeup

## Challenge [1/3]: Network Analysis & Payload Recovery
1. Open `nit_breach_1_3.pcap` in Wireshark.
2. Filter through the background noise to identify the true attack traffic between `172.16.50.133` (Attacker) and `172.16.50.100` (Victim).
3. Follow the TCP stream for the Telnet negotiation on port 23. You will observe the attacker exploiting **CVE-2026-24061** via the `NEW-ENVIRON` sub-negotiation to establish a reverse shell on port 4444.
   *(Flag 1: `nmctf{172.16.50.133_172.16.50.100_2.4.59_CVE-2026-24061_4444}`)*
4. Follow the reverse shell traffic on port 4444 to view the attacker's bash history. Observe the command used to encrypt the payload:
   `openssl enc -aes-256-cbc -pbkdf2 -pass pass:$(date +%s) -in research_backup.zip -out exfiltrated.dat`
5. The attacker exfiltrated `exfiltrated.dat` via an HTTP POST request. You can recover it easily:
   - Filter for `http.request.method == POST` in Wireshark.
   - Right-click the packet, go to **Follow > HTTP Stream**.
   - The payload is a Base64-encoded string (the `data=` field).
   - Copy the Base64 string and decode it (e.g. using CyberChef or `base64 -d`) to recover the raw `exfiltrated.dat` binary.

## Challenge [2/3]: Memory Forensics (Deleted InnoDB File Recovery)

1. The memory dump `nit_breach_2.raw` was captured using LiME (lime format) on the server after the attacker deleted the MariaDB database files while MariaDB was still running. Linux only unlinks the directory entry — the file data stays in the kernel page cache until the last file handle closes.

2. Download the Volatility 3 ISF symbols for kernel `6.8.0-90-generic` (Ubuntu 24.04):
   ```bash
   wget https://github.com/Abyss-W4tcher/volatility3-symbols/raw/master/Ubuntu/amd64/6.8.0/90/generic/Ubuntu_6.8.0-90-generic_6.8.0-90.91_amd64.json.xz -P <vol3>/volatility3/symbols/linux/
   ```

3. **Find the database process:**
   ```bash
   vol -f nit_breach_2.raw linux.pslist.PsList
   ```
   → Shows `mariadbd` running as PID 3105.

4. **Find the deleted file handles** (this is the key insight — `lsof` shows the file is still open even though deleted):
   ```bash
   vol -f nit_breach_2.raw linux.lsof.Lsof --pid 3105
   ```
   → Shows:
   ```
   /var/lib/mysql/nit_numidian_db/classified_secrets.ibd (deleted)  fd=78  size=65536
   /var/lib/mysql/nit_numidian_db/core_configuration.ibd (deleted)   fd=79  size=65536
   ```

5. **Confirm the page cache:**
   ```bash
   vol -f nit_breach_2.raw linux.pagecache.Files
   ```
   → Lists the same `.ibd` files as cached (inode 266980 and 266982, 65536 bytes each).

6. **Extract and decode the flag.** The InnoDB data pages are 16KB. The classified secret is stored as a **hex-encoded** value in the `telemetry_encryption_key` column. Search the raw dump for the InnoDB record marker and extract the data page:
   ```python
   import re
   data = open("nit_breach_2.raw","rb").read()
   hex_flag = b"6e6d6374667b6e756d316431346e5f6d336d3072795f7333637233745f3763326238617d"
   pos = data.find(hex_flag)
   page_start = pos - (pos % 16384)
   print(data[page_start:page_start+16384].split(b"telemetry_encryption_key")[1][:120])
   ```
   Output: `telemetry_encryption_key6e6d6374667b6e756d316431346e5f6d336d3072795f7333637233745f3763326238617d`

7. **Decode the hex:**
   ```python
   bytes.fromhex("6e6d6374667b6e756d316431346e5f6d336d3072795f7333637233745f3763326238617d").decode()
   ```
   → `nmctf{num1d14n_m3m0ry_s3cr3t_7c2b8a}`

   *(Flag 2: `nmctf{num1d14n_m3m0ry_s3cr3t_7c2b8a}`)*

## Challenge [3/3]: Exfiltration, Cryptography & Font Obfuscation

### Step 1: Extract Exfiltrated Data from PCAP
1. The attacker exfiltrated `exfiltrated.dat` via an HTTP POST request in the PCAP.
2. Filter for `http.request.method == POST` in Wireshark.
3. Right-click the packet, go to **Follow > HTTP Stream**.
4. The payload is a Base64-encoded string. Copy and decode it to recover the raw `exfiltrated.dat` binary.

#### Step 2: Cryptography (Decryption)
1. The attacker used the Unix timestamp of the attack as the encryption password.
2. Look at the timestamp of the packets during the encryption phase (e.g., June 17, 2026, approx 10:10:23 UTC).
3. Convert this time to a Unix epoch timestamp: `1718657423`.
4. Decrypt the file:
   `openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:1718657423 -in exfiltrated.dat -out research_backup.zip`
5. Unzip the archive to retrieve `numidian_core_status.pdf`.

### Step 3: Font-Level Deobfuscation
1. Opening `numidian_core_status.pdf` reveals the token section visually rendering as garbled gibberish: `ILTVYXZ-+=^<>/\|~.,:;'\"()[]_!*?l#@`
2. Attempting to copy-paste the text yields a fake flag: `nmctf{f4k3_fl4g_l0l_try_h4rd3r_!}`
3. Running `qpdf` or `peepdf` to view the raw decompressed PDF stream reveals another fake layer: `abcdefghijklmnopqrstuvwxyz01234567`.
4. **The Trick:** The real flag is encoded entirely within the **vector coordinates** of the custom TrueType font embedded in the PDF.
5. Extract the font using `mutool extract numidian_core_status.pdf` or `peepdf`, obtaining a `.ttf` file.
6. Convert the `.ttf` to XML using `ttx` (from Python's `fonttools` suite).
7. Inspect the `<glyf>` definitions for the gibberish characters. The script artificially padded the vector contours of each glyph so that the **total number of coordinate points (`<pt>` tags)** exactly matches the ASCII value of the real flag's characters.
8. Write a script (or manually count) to map the point counts to ASCII:
   - Glyph `I` -> 110 points -> `n`
   - Glyph `L` -> 109 points -> `m`
   - Glyph `T` -> 99 points -> `c`
   - Glyph `V` -> 116 points -> `t`
   ...
9. Reconstructing these ASCII values reveals the true flag:
   `nmctf{num1d14n_c0r3_r3p0rt_9e1f5d}`
