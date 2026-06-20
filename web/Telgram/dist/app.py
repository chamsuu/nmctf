import base64
import csv
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask, g, jsonify, render_template, request, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
import secrets

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(APP_ROOT, "instance")
EXPORT_DIR = os.path.join(INSTANCE_DIR, "exports")
DB_PATH = os.path.join(INSTANCE_DIR, "mischief.db")
INIT_SQL_PATH = os.path.join(APP_ROOT, "init.sql")

FLAG1 = os.environ.get("FLAG1", "nmctf{part_1")
FLAG2 = os.environ.get("FLAG2", "part_2}")
ADMIN1_PASSWORD = os.environ.get("ADMIN1_PASSWORD", "password_admin1")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password_admin")

ADMIN1_CREATED_AT = "don't change this value"
ADMIN1_EMAIL = "admin@gmail.com"
ADMIN_CREATED_AT = "don't change this value"   
ADMIN_EMAIL = f"{uuid.uuid4().hex[:16]}@telgram.meduim"

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

KEY_DIR = os.path.join(INSTANCE_DIR, "keys")
PRIV_KEY_PATH = os.path.join(KEY_DIR, "private.pem")
PUB_KEY_PATH = os.path.join(KEY_DIR, "public.pem")
PRIVATE_KEY = None
PUBLIC_KEY = None


def load_or_generate_keys():
    global PRIVATE_KEY, PUBLIC_KEY

    print("[+] Key directory:", KEY_DIR)
    print("[+] Private key path:", PRIV_KEY_PATH)
    print("[+] Public key path:", PUB_KEY_PATH)

    os.makedirs(KEY_DIR, exist_ok=True)

    if os.path.exists(PRIV_KEY_PATH):
        print("[*] Existing key found. Loading from disk...")

        with open(PRIV_KEY_PATH) as f:
            PRIVATE_KEY = f.read()

        with open(PUB_KEY_PATH) as f:
            PUBLIC_KEY = f.read()

        print("[+] Private key loaded (first 60 chars):")
        print(PRIVATE_KEY[:60])

        print("[+] Public key loaded (first 60 chars):")
        print(PUBLIC_KEY[:60])

    else:
        print("[!] No existing key found. Generating new RSA keypair...")

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        PRIVATE_KEY = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        PUBLIC_KEY = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        print("[+] New private key generated (first 60 chars):")
        print(PRIVATE_KEY[:60])

        print("[+] New public key generated (first 60 chars):")
        print(PUBLIC_KEY[:60])

        with open(PRIV_KEY_PATH, "w") as f:
            f.write(PRIVATE_KEY)

        with open(PUB_KEY_PATH, "w") as f:
            f.write(PUBLIC_KEY)

        print("[+] Keys saved to disk")


def now_string():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def user_id_from_timestamp(timestamp):
    return hashlib.md5(f"{timestamp}".encode()).hexdigest()


def generate_chat_id(owner_id, peer_username):
    seed = f"{owner_id}:{peer_username}"
    return int(hashlib.md5(seed.encode()).hexdigest()[:6], 16) % 90000 + 10000


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def render_init_sql(context):
    with open(INIT_SQL_PATH, encoding="utf-8") as handle:
        script = handle.read()
    for key, value in context.items():
        script = script.replace("{{" + key + "}}", sql_literal(value))
    return script


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        admin1_id = user_id_from_timestamp(ADMIN1_CREATED_AT)
        admin_id = user_id_from_timestamp(ADMIN_CREATED_AT)
        admin1_chat_id = generate_chat_id(admin1_id, "System Administrator")
        admin_chat_id = generate_chat_id(admin_id, "System Administrator")
        db.executescript(
            render_init_sql(
                {
                    "ADMIN1_ID": admin1_id,
                    "ADMIN1_EMAIL": ADMIN1_EMAIL,
                    "ADMIN1_PASSWORD_HASH": generate_password_hash(ADMIN1_PASSWORD),
                    "ADMIN1_CREATED_AT": ADMIN1_CREATED_AT,
                    "ADMIN1_CHAT_ID": admin1_chat_id,
                    "ADMIN_ID": admin_id,
                    "ADMIN_EMAIL": ADMIN_EMAIL,
                    "ADMIN_PASSWORD_HASH": generate_password_hash(ADMIN_PASSWORD),
                    "ADMIN_CREATED_AT": ADMIN_CREATED_AT,
                    "ADMIN_CHAT_ID": admin_chat_id,
                    "FLAG1": FLAG1,
                    "FLAG2": FLAG2,
                }
            )
        )
        db.commit()


def make_token(user):
    payload = {
        "username": user["username"],
        "email": user["email"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=4),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


def b64_decode(data):
    data = data.encode() if isinstance(data, str) else data
    rem = len(data) % 4
    if rem:
        data += b"=" * (4 - rem)
    return base64.urlsafe_b64decode(data)


def decode_token(token):
    try:
        return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    except jwt.PyJWTError:
        pass
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header = json.loads(b64_decode(parts[0]))
        if header.get("alg") != "HS256":
            return None
        payload = json.loads(b64_decode(parts[1]))
        signing_input = f"{parts[0]}.{parts[1]}".encode()
        expected_sig = hmac.new(PUBLIC_KEY.encode(), signing_input, hashlib.sha256).digest()
        actual_sig = b64_decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None
        return payload
    except Exception:
        return None


def socket_payload(auth=None):
    token = None
    if isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        token = request.args.get("token")
    return decode_token(token or "")


def current_user_from_socket(auth=None):
    payload = socket_payload(auth)
    if not payload:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE username = ? AND email = ?",
        (payload.get("username"), payload.get("email", "")),
    ).fetchone()


def current_user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    payload = decode_token(header.removeprefix("Bearer ").strip())
    if not payload:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE username = ? AND email = ?",
        (payload.get("username"), payload.get("email", "")),
    ).fetchone()


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user_from_request()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400
    if len(username) > 32 or not username.replace("_", "").isalnum():
        return jsonify({"error": "Use 1-32 letters, numbers, or underscores"}), 400
    if "@" not in email or len(email) > 128:
        return jsonify({"error": "Invalid email"}), 400

    db = get_db()
    created_at = now_string()
    user_id = user_id_from_timestamp(created_at)
    try:
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, created_at, Bio_public, Bio_private) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, email, generate_password_hash(password), created_at,
             "This user prefers to keep an air of mystery about them.",
             "No private information set."),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 409

    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify({"token": make_token(user), "user": public_user(user)})


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401
    return jsonify({"token": make_token(user), "user": public_user(user)})


@app.get("/api/me")
@require_auth
def me():
    return jsonify({"user": public_user(g.current_user)})


@app.get("/api/auth/validate")
@require_auth
def validate_auth():
    return jsonify({"user": public_user(g.current_user)})


@app.get("/api/chats")
@require_auth
def chats():
    target_user_id = request.args.get("user_id") or g.current_user["id"]
    target = get_db().execute(
        "SELECT id, username FROM users WHERE id = ?", (target_user_id,)
    ).fetchone()
    if target is None:
        return jsonify({"error": "User not found"}), 404
    rows = get_db().execute(
        "SELECT * FROM chats WHERE owner_id = ? OR peer_username = ? ORDER BY created_at DESC",
        (target["id"], target["username"]),
    ).fetchall()
    return jsonify({"chats": [dict(row) for row in rows]})


@app.get("/api/chats/<int:chat_id>/messages")
@require_auth
def messages(chat_id):
    chat = get_db().execute(
        "SELECT id FROM chats WHERE id = ? AND (owner_id = ? OR peer_username = ?)",
        (chat_id, g.current_user["id"], g.current_user["username"]),
    ).fetchone()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    rows = get_db().execute(
        "SELECT sender, body, created_at FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    return jsonify({"messages": [dict(row) for row in rows]})


@app.post("/api/chats/create")
@require_auth
def create_chat():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    target = get_db().execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
    if target is None:
        return jsonify({"error": f"No user named {username}"}), 404
    if target["id"] == g.current_user["id"]:
        return jsonify({"error": "Choose another user"}), 400

    created_at = now_string()
    chat_id = generate_chat_id(g.current_user["id"], target["username"])
    get_db().execute(
        "INSERT INTO chats (id, owner_id, peer_username, title, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, g.current_user["id"], target["username"], f"Chat with {target['username']}", created_at),
    )
    get_db().execute(
        "INSERT INTO messages (chat_id, sender, body, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, "system", f"Secure room opened with {target['username']}. 49!!", created_at),
    )
    get_db().commit()
    chat = get_db().execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    return jsonify({"chat_id": chat_id, "chat": dict(chat), "message": "Chat created"})


@app.post("/api/chats/<int:chat_id>/messages")
@require_auth
def send_message(chat_id):
    chat = get_db().execute(
        "SELECT id FROM chats WHERE id = ? AND (owner_id = ? OR peer_username = ?)",
        (chat_id, g.current_user["id"], g.current_user["username"]),
    ).fetchone()
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404

    data = request.get_json(silent=True) or {}
    body = (data.get("content") or data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Message body is required"}), 400
    if len(body) > 500:
        return jsonify({"error": "Message body is too long"}), 400

    created_at = now_string()
    cursor = get_db().execute(
        "INSERT INTO messages (chat_id, sender, body, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, g.current_user["username"], body, created_at),
    )
    get_db().commit()
    message = {
        "id": cursor.lastrowid,
        "chat_id": chat_id,
        "sender": g.current_user["username"],
        "body": body,
        "created_at": created_at,
    }
    socketio.emit(
        "message_created",
        {"chat_id": chat_id, "message": message},
        to=f"chat_{chat_id}",
    )
    return jsonify({"message": message})


@app.get("/api/exports")
@require_auth
def list_exports():
    rows = get_db().execute(
        "SELECT id, filename, target_user_id, created_at FROM exports WHERE requester_id = ? ORDER BY created_at DESC",
        (g.current_user["id"],),
    ).fetchall()
    return jsonify({"exports": [dict(row) for row in rows]})


@app.get("/api/download/<export_id>")
@require_auth
def download_export(export_id):
    row = get_db().execute(
        "SELECT * FROM exports WHERE id = ? AND requester_id = ?",
        (export_id, g.current_user["id"]),
    ).fetchone()
    if row is None:
        return jsonify({"error": "Export not found"}), 404
    path = os.path.join(EXPORT_DIR, row["filename"])
    return send_file(path, as_attachment=True, download_name=row["filename"])


@app.get("/api/users")
@require_auth
def user_stats():
    rows = get_db().execute(
        """
        SELECT
            substr(created_at, 1, 10) AS date,
            min(created_at) AS first_registration,
            max(created_at) AS last_registration,
            count(*) AS user_count
        FROM users
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date
        """
    ).fetchall()
    return jsonify({"stats": [dict(row) for row in rows]})


@app.get("/pubkey")
def pubkey():
    return PUBLIC_KEY, 200, {"Content-Type": "text/plain"}


@app.get("/api/profile/<user_id>")
@require_auth
def public_profile(user_id):
    user = get_db().execute(
        "SELECT username, created_at, Bio_public FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    created = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
    years = (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).days // 365
    if years < 1:
        joined = "Joined this year"
    else:
        joined = f"Joined {years} years ago"
    return jsonify({"profile": {
        "username": user["username"],
        "joined": joined,
        "bio": user["Bio_public"],
    }})


@app.get("/api/profile/private")
@require_auth
def private_profile():
    return jsonify({"profile": {
        "username": g.current_user["username"],
        "bio_public": g.current_user["Bio_public"],
        "bio_private": g.current_user["Bio_private"],
    }})


@socketio.on("connect")
def socket_connect(auth):
    payload = socket_payload(auth)
    if payload is None:
        return False


@socketio.on("export_chats")
def export_chats(data):
    token = request.args.get("token")
    payload = decode_token(token or "")
    if payload is None:
        emit("export_failed", {"error": "Authentication required"})
        return

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    requester = db.execute(
        "SELECT id FROM users WHERE username = ? AND email = ?",
        (payload.get("username"), payload.get("email", "")),
    ).fetchone()
    if requester is None:
        emit("export_failed", {"error": "Authentication required"})
        db.close()
        return

    requester_id = requester["id"]
    target_user_id = (data or {}).get("user_id", "")
    if target_user_id != requester_id:
        emit("export_failed", {"error": "You can only export your own data"})
        db.close()
        return
    export_type = (data or {}).get("export_type", "all")
    if export_type != "all":
        emit("export_failed", {"error": "Unsupported export type"})
        db.close()
        return

    target = db.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if target is None:
        emit("export_failed", {"error": "Target user not found"})
        db.close()
        return

    export_id = hashlib.md5(f"{requester_id}:{target_user_id}:{now_string()}".encode()).hexdigest()
    filename = f"chat_export_{target['username']}_{export_id[:8]}.csv"
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["chat_title", "peer", "sender", "message", "timestamp"])
        rows = db.execute(
            """
            SELECT c.title, c.peer_username, m.sender, m.body, m.created_at
            FROM chats c
            JOIN messages m ON m.chat_id = c.id
            WHERE c.owner_id = ? OR c.peer_username = ?
            ORDER BY c.id, m.id
            """,
            (target_user_id, target["username"]),
        ).fetchall()
        for row in rows:
            writer.writerow([row["title"], row["peer_username"], row["sender"], row["body"], row["created_at"]])

    db.execute(
        "INSERT INTO exports (id, requester_id, target_user_id, filename, created_at) VALUES (?, ?, ?, ?, ?)",
        (export_id, requester_id, target_user_id, filename, now_string()),
    )
    db.commit()
    db.close()
    emit(
        "export_completed",
        {
            "message": "Export completed successfully. Check downloads in Settings.",
            "export_id": export_id,
            "filename": filename,
            "target_user": target["username"],
        },
    )


@socketio.on("join_chat")
def join_chat(data):
    user = current_user_from_socket()
    if user is None:
        emit("chat_error", {"error": "Authentication required"})
        return

    chat_id = (data or {}).get("chat_id")
    if not chat_id:
        emit("chat_error", {"error": "Chat id required"})
        return

    chat = get_db().execute(
        "SELECT id, title FROM chats WHERE id = ?",
        (chat_id,),
    ).fetchone()
    if chat is None:
        emit("chat_error", {"error": "Chat not found"})
        return

    join_room(f"chat_{chat_id}")
    rows = get_db().execute(
        "SELECT sender, body, created_at FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    emit("chat_joined", {
        "chat_id": chat_id,
        "title": chat["title"],
        "messages": [dict(row) for row in rows],
    })


@socketio.on("leave_chat")
def leave_chat(data):
    chat_id = (data or {}).get("chat_id")
    if not chat_id:
        return
    leave_room(f"chat_{chat_id}")


def public_user(user):
    return {"id": user["id"], "username": user["username"], "created_at": user["created_at"]}


load_or_generate_keys()
init_db()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), allow_unsafe_werkzeug=True)
