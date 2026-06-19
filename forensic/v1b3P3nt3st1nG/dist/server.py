#!/usr/bin/env python3
"""
v1b3P3nt3st1nG — DFIR Forensics Challenge
nc-based sequential question server.
One wrong answer = connection dies.
"""
import socket
import threading
import signal
import sys
import re

HOST = '0.0.0.0'
PORT = 4444
TIMEOUT = 300  # 5 min per question
FLAG = 'nmctf{n0w_u_und3r574nd_0p3nc0d3_1nn3r_f1l35}'

BANNER = r"""
                _  _ ___   ___  ___  ___  _  _ 
 __ _____ _ _ | || |__ / | _ \/ _ \| _ \| |/ /
  \ V / -_) ' \| || ||_ \ |  _/ (_) |  _/|   < 
   \_/\___|_||_|_||_|___/ |_|  \___/|_|  |_|\_\

"""

INTRO = """============================================================
  FORENSIC INVESTIGATION — Coco's Compromised Workstation
============================================================

Coco's Ubuntu workstation was compromised. We've acquired a
forensic image of her system. An attacker gained access,
escalated to root, and used an unconventional platform directly
on the machine — leaving behind configuration files, session logs,
and database artifacts.

Your mission: analyze the forensic image and answer 12 questions.
One wrong answer and the connection terminates.
============================================================
"""

QUESTIONS = [
    {
        'id': 1,
        'title': 'Patient Zero',
        'text': 'How did the attacker initially gain access to Coco\'s machine? What was the filename of the malicious payload that Coco executed?',
        'format': 'filename',
        'answers': ['invoice_2026.pdf', 'invoice_2026.pdf.sh'],
    },
    {
        'id': 2,
        'title': 'Elevation',
        'text': 'After gaining initial access, the attacker escalated privileges using a known vulnerability. What is the CVE identifier?',
        'format': 'CVE-XXXX-XXXXX',
        'answers': ['CVE-2026-31431', 'cve-2026-31431'],
    },
    {
        'id': 3,
        'title': 'Knock Knock',
        'text': 'What is the exact UTC timestamp when the attacker obtained root access on the system?',
        'format': 'YYYY-MM-DD HH:MM:SS',
        'answers': ['2026-06-02 09:17:44'],
    },
    {
        'id': 4,
        'title': 'Staying Power',
        'text': 'The attacker created a persistence mechanism disguised as a GNOME component. What is the full command that the malicious autostart entry executes?',
        'format': 'the full command',
        'answers': [
            "/bin/bash -c 'bash /home/coco/.local/share/.cache/system-update.sh'",
            '/bin/bash -c "bash /home/coco/.local/share/.cache/system-update.sh"',
        ],
    },
    {
        'id': 5,
        'title': 'The Unusual Suspect',
        'text': 'Among the artifacts is a directory belonging to a tool the attacker used directly on the machine. What is the full path to this tool\'s data directory?',
        'format': '/full/path/to/dir',
        'answers': ['/home/coco/.local/share/opencode'],
    },
    {
        'id': 6,
        'title': 'First Words',
        'text': 'The attacker used opencode extensively. What was the very first prompt they sent to it? Provide the exact text.',
        'format': 'exact prompt text',
        'answers': [
            'I just got root via a copy.fail exploit. Enumerate this system — users, SUID binaries, writable dirs, running services, network config.',
            'I just got root via a copy.fail exploit. Enumerate this system - users, SUID binaries, writable dirs, running services, network config.',
        ],
    },
    {
        'id': 7,
        'title': 'Engine Room',
        'text': 'The attacker configured opencode to use a specific AI model. What is the exact model identifier they used?',
        'format': 'provider/model-name',
        'answers': ['opencode-go/qwen3.7-max', 'qwen3.7-max'],
    },
    {
        'id': 8,
        'title': 'Persistence Chain',
        'text': 'The attacker asked opencode to create multiple files for persistence. What are the filenames of the three files?',
        'format': 'file1|file2|file3 (any order)',
        'answers': ['system-update-check.timer|system-update-check.service|org.gnome.Software.UpdateNotifier.desktop'],
        'unordered': True,
    },
    {
        'id': 9,
        'title': 'The Mole',
        'text': 'The attacker configured opencode with a remote MCP server for C2. The config has been cleaned. What URL and authentication header value did they use?',
        'format': 'url|header_value',
        'answers': ['https://c2.sandstone-op.net/mcp|r0cky-s4ndst0n3'],
    },
    {
        'id': 10,
        'title': 'Harvest',
        'text': 'The attacker wrote a Python script to steal Chrome saved passwords. What is the SHA256 hash of the final version of that script?',
        'format': '64-character hex string',
        'answers': ['07a2aed6ed6a2f9ba2bfff6a07dbd3bdb783bf5de3e9626f33b05166d083292a'],
    },
    {
        'id': 11,
        'title': 'Ghost Sessions',
        'text': 'The attacker deleted several opencode sessions to hide tracks. A deleted session discusses DNS-based data exfiltration. What domain did the attacker specify?',
        'format': 'domain.tld',
        'answers': ['exfil.sandstone-op.net'],
    },
    {
        'id': 12,
        'title': 'Classify',
        'text': 'The deleted DNS exfiltration session contains multiple attack activities. What is the most specific MITRE ATT&CK sub-technique ID for the primary exfiltration method used?',
        'format': 'TXXXX.XXX',
        'answers': ['T1048.003', 't1048.003'],
    },
]


def normalize(s):
    """Strip whitespace and normalize quotes for comparison."""
    s = s.strip()
    s = s.replace('\u2014', '-').replace('\u2013', '-')  # normalize dashes
    s = s.replace('\u2018', "'").replace('\u2019', "'")  # smart quotes
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    return s


def check_answer(q, answer):
    """Check if answer matches any accepted value for the question."""
    answer = normalize(answer)

    if q.get('unordered'):
        # Q8: filenames can be in any order
        expected_set = set(q['answers'][0].split('|'))
        given_set = set(answer.split('|'))
        return expected_set == given_set

    return answer in [normalize(a) for a in q['answers']]


def handle_client(conn, addr):
    """Handle a single client connection."""
    try:
        conn.settimeout(TIMEOUT)
        conn.sendall(BANNER.encode())
        conn.sendall(INTRO.encode())

        for q in QUESTIONS:
            # Send question
            msg = (
                f"\n{'─' * 60}\n"
                f"  [{q['id']:02d}/12] {q['title']}\n"
                f"{'─' * 60}\n"
                f"  {q['text']}\n"
                f"\n  Format: {q['format']}\n"
                f"\n  Your answer: "
            )
            conn.sendall(msg.encode())

            # Receive answer
            data = b''
            try:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        raise ConnectionError("client disconnected")
                    data += chunk
                    if b'\n' in data:
                        break
            except socket.timeout:
                conn.sendall(b"\n\n[!] Timeout exceeded. Connection closed.\n")
                return

            answer = data.decode('utf-8', errors='replace').strip()

            if check_answer(q, answer):
                conn.sendall(b"\n  [*] Correct!\n")
            else:
                lines = [
                    "",
                    "  [x] Wrong answer.",
                    "",
                    "  The investigation has been compromised.",
                    "  Connection terminated.",
                    "",
                ]
                conn.sendall('\n'.join(lines).encode())
                return

        # All 12 correct — deliver the flag
        lines = [
            "",
            "=" * 60,
            "  INVESTIGATION COMPLETE — ALL 12 QUESTIONS ANSWERED",
            "=" * 60,
            "",
            f"  Flag: {FLAG}",
            "",
            "  Congratulations. You've reconstructed the attack chain",
            "  and understand how agentic AI tools leave forensic traces.",
            "=" * 60,
            "",
        ]
        conn.sendall('\n'.join(lines).encode())

    except (ConnectionError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    # Handle Ctrl+C gracefully
    def shutdown(sig, frame):
        print("\n[!] Server shutting down.")
        server.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[+] v1b3P3nt3st1nG server listening on {HOST}:{PORT}")
    print(f"[+] Connect with: nc localhost {PORT}")
    print(f"[+] {len(QUESTIONS)} questions, one wrong answer = disconnect\n")

    while True:
        try:
            conn, addr = server.accept()
            print(f"[+] Connection from {addr[0]}:{addr[1]}")
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except OSError:
            break


if __name__ == '__main__':
    main()
