#!/usr/bin/env python3
"""
el camel - Blind SSRF Challenge
Flask backend with Base64 bypass vulnerability
"""

import base64
import logging
import socket
from urllib.parse import urlparse

import requests
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("el-camel")

# Denylist — runs BEFORE Base64 decoding (the intentional flaw)
DENYLIST_PATTERNS = [
    "127.0.0.1",
    "localhost",
    "internal-logger",
]

# Timeout for outbound requests to prevent abuse
REQUEST_TIMEOUT = 10


def check_filter(url: str) -> bool:
    """Check if URL contains any denylisted patterns.
    Returns True if BLOCKED (threat detected)."""
    url_lower = url.lower()
    for pattern in DENYLIST_PATTERNS:
        if pattern in url_lower:
            logger.warning(f"Filter blocked URL containing '{pattern}': {url[:100]}")
            return True
    return False


def fetch_url(target_url: str) -> dict:
    """
    Fetch the target URL but NEVER return the response body.
    This makes it a Blind SSRF.
    """
    try:
        logger.info(f"Fetching URL: {target_url[:150]}")
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https"):
            return {"status": "error", "msg": "Only HTTP/HTTPS URLs are supported."}

        # Resolve DNS to catch internal hostnames
        hostname = parsed.hostname
        try:
            addr = socket.gethostbyname(hostname)
            logger.info(f"Resolved {hostname} -> {addr}")
        except socket.gaierror:
            return {"status": "error", "msg": "Could not resolve hostname."}

        resp = requests.get(
            target_url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "el-camel-validator/1.0"},
        )
        # Blind — we never return the response body
        logger.info(f"Fetched {target_url[:100]} -> HTTP {resp.status_code} ({len(resp.content)} bytes)")
        return {"status": "safe", "msg": "No threats found"}

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching URL: {target_url[:100]}")
        return {"status": "error", "msg": "Request timed out."}
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error: {e}")
        return {"status": "error", "msg": "Could not connect to the endpoint."}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"status": "error", "msg": "An unexpected error occurred."}


@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@app.route("/docs/api-internal.txt")
def api_docs():
    """Deliberately exposed internal docs — hidden hint for competitors."""
    return send_from_directory("docs", "api-internal.txt")


@app.route("/api/ride-camel", methods=["POST"])
def ride_camel():
    """
    Main vulnerable endpoint.
    
    Accepts:
      - service_url: plaintext URL
      - raw_ride: Base64-encoded URL (bypasses denylist because 
                  filter runs BEFORE decoding)
    """
    data = request.get_json(silent=True) or {}
    raw_ride = data.get("raw_ride")
    service_url = data.get("service_url")

    # Determine the URL source
    if raw_ride:
        # ===== THE FLAW =====
        # Filter runs on the RAW Base64 string BEFORE decoding.
        # Since Base64-encoded data won't contain patterns like 
        # "localhost" or "internal-logger", the filter is effectively
        # bypassed for any URL wrapped in Base64.
        # =====================
        if check_filter(raw_ride):
            return jsonify({"status": "blocked", "msg": "Security threat detected!"}), 403

        # Decode AFTER the filter check (the bypass opportunity)
        try:
            decoded_bytes = base64.b64decode(raw_ride, validate=True)
            target_url = decoded_bytes.decode("utf-8")
            logger.info(f"Decoded raw_ride -> {target_url[:150]}")
        except (base64.binascii.Error, ValueError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid Base64 in raw_ride: {e}")
            return jsonify({"status": "error", "msg": "Invalid Base64 encoding."}), 400

    elif service_url:
        # Plaintext URL — filter checks the actual URL content
        target_url = service_url
        if check_filter(target_url):
            return jsonify({"status": "blocked", "msg": "Security threat detected!"}), 403
    else:
        return jsonify({"status": "error", "msg": "Missing service_url or raw_ride parameter."}), 400

    # Execute the fetch
    result = fetch_url(target_url)
    status_code = 200 if result["status"] in ("safe",) else 400
    return jsonify(result), status_code


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    logger.info("el camel validator starting on port 80...")
    app.run(host="0.0.0.0", port=80, debug=False)
