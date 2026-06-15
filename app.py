from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
FRONTEND = PROJECT_ROOT / "frontend"
DB_PATH = ROOT / "goldtrace.db"
SECRET = os.environ.get("GOLDTRACE_SECRET", "dev-secret-change-me")
TOKEN_TTL_SECONDS = 60 * 60 * 8
DEMO_PASSWORD = "GoldTrace!2026"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"pbkdf2_sha256${salt}${base64.b64encode(digest).decode()}"


def verify_password(password, stored):
    try:
        _, salt, encoded = stored.split("$", 2)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_token(payload):
    payload = {**payload, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{b64url(sig)}"


def parse_token(token):
    try:
        body, sig = token.split(".", 1)
        expected = b64url(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def rows(cur):
    return [dict(row) for row in cur.fetchall()]


def init_db():
    first_run = not DB_PATH.exists()
    with db() as conn:
        conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        seed_sql = (ROOT / "seed.sql").read_text(encoding="utf-8")
        seed_sql = seed_sql.replace("PBKDF2_PLACEHOLDER", hash_password(DEMO_PASSWORD))
        conn.executescript(seed_sql)
        if first_run:
            print(f"Seeded database at {DB_PATH}")


def latest_previous_hash(conn, batch_id):
    row = conn.execute(
        "SELECT event_hash FROM ledger_events WHERE batch_id = ? ORDER BY datetime(created_at) DESC, id DESC LIMIT 1",
        (batch_id,),
    ).fetchone()
    return row["event_hash"] if row else None


def event_hash(batch_id, actor_org_id, event_type, notes, previous_hash):
    raw = f"{batch_id}|{actor_org_id}|{event_type}|{notes}|{previous_hash or ''}|{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def audit_log(conn, user, action, ip, details):
    conn.execute(
        "INSERT INTO audit_log (user_id, action, ip_address, details) VALUES (?, ?, ?, ?)",
        (user.get("id") if user else None, action, ip, json.dumps(details)),
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "KaramojaGoldTrace/1.0"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:")
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.route("GET", parsed.path)
        return self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        return self.route("POST", parsed.path)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except json.JSONDecodeError:
            self.error(400, "Invalid JSON body")
            return None

    def json(self, status, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error(self, status, message):
        self.json(status, {"error": message})

    def auth(self, allowed=None):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            self.error(401, "Missing bearer token")
            return None
        payload = parse_token(header[7:])
        if not payload:
            self.error(401, "Invalid or expired token")
            return None
        if allowed and payload.get("role") not in allowed:
            self.error(403, "Role is not authorized for this operation")
            return None
        return payload

    def route(self, method, path):
        if method == "POST" and path == "/api/auth/login":
            return self.login()
        routes = {
            ("GET", "/api/me"): self.me,
            ("GET", "/api/dashboard"): self.dashboard,
            ("GET", "/api/ledger"): self.ledger,
            ("GET", "/api/batches"): self.batches,
            ("POST", "/api/batches"): self.create_batch,
            ("GET", "/api/escrows"): self.escrows,
            ("GET", "/api/mining-blocks"): self.mining_blocks,
            ("GET", "/api/audits"): self.audits,
            ("POST", "/api/audits"): self.create_audit,
            ("GET", "/api/prices"): self.prices,
        }
        if method == "POST" and path.startswith("/api/escrows/") and path.endswith("/release"):
            return self.release_escrow(path)
        handler = routes.get((method, path))
        if not handler:
            return self.error(404, "Route not found")
        return handler()

    def serve_static(self, path):
        target = FRONTEND / ("index.html" if path in ("", "/") else path.lstrip("/"))
        if not target.exists() or not target.resolve().is_relative_to(FRONTEND.resolve()):
            target = FRONTEND / "index.html"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def login(self):
        body = self.read_json()
        if body is None:
            return
        email = body.get("email", "").strip().lower()
        password = body.get("password", "")
        with db() as conn:
            user = conn.execute(
                """SELECT users.*, organizations.name AS organization_name
                   FROM users JOIN organizations ON organizations.id = users.organization_id
                   WHERE email = ? AND is_active = 1""",
                (email,),
            ).fetchone()
            ok = user and verify_password(password, user["password_hash"])
            audit_log(conn, dict(user) if user else None, "auth.login", self.client_address[0], {"email": email, "success": bool(ok)})
            if not ok:
                return self.error(401, "Invalid credentials")
            payload = {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "organization_id": user["organization_id"],
                "name": user["full_name"],
            }
            self.json(200, {"token": sign_token(payload), "user": payload | {"organization_name": user["organization_name"]}})

    def me(self):
        user = self.auth()
        if user:
            self.json(200, {"user": user})

    def dashboard(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            totals = conn.execute(
                """SELECT COUNT(*) batches, ROUND(SUM(gross_weight_g), 2) grams,
                          ROUND(SUM(gross_weight_g * purity_pct / 100), 2) fine_grams
                   FROM gold_batches"""
            ).fetchone()
            escrow = conn.execute(
                "SELECT status, ROUND(SUM(amount_usd), 2) amount FROM escrows GROUP BY status"
            ).fetchall()
            audit = conn.execute("SELECT ROUND(AVG(score), 1) avg_score, MIN(score) min_score FROM ethical_audits").fetchone()
            status = conn.execute("SELECT status, COUNT(*) count FROM gold_batches GROUP BY status").fetchall()
            latest_price = conn.execute("SELECT * FROM gold_prices ORDER BY datetime(captured_at) DESC LIMIT 1").fetchone()
            blocks = conn.execute("SELECT environmental_status, COUNT(*) count FROM mining_blocks GROUP BY environmental_status").fetchall()
            self.json(200, {
                "totals": dict(totals),
                "escrow_by_status": rows_from(escrow),
                "audit": dict(audit),
                "batch_status": rows_from(status),
                "latest_price": dict(latest_price),
                "block_environment": rows_from(blocks),
                "benefits": [
                    "Transparency: every gram is traceable from licensed block to export.",
                    "Fair Trade: miners receive equitable prices with premiums visible.",
                    "Security: buyer funds are protected through escrow milestones.",
                    "Compliance: ethical and environmental standards are enforced.",
                    "Market Confidence: buyers can verify certified gold provenance."
                ],
            })

    def ledger(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            data = conn.execute(
                """SELECT ledger_events.*, gold_batches.batch_code, organizations.name actor
                   FROM ledger_events
                   JOIN gold_batches ON gold_batches.id = ledger_events.batch_id
                   JOIN organizations ON organizations.id = ledger_events.actor_org_id
                   ORDER BY datetime(ledger_events.created_at) DESC, ledger_events.id DESC"""
            )
            self.json(200, {"events": rows(data)})

    def batches(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            cur = conn.execute(
                """SELECT b.*, mb.block_code, mb.district, holder.name current_holder, coop.name cooperative
                   FROM gold_batches b
                   JOIN mining_blocks mb ON mb.id = b.mining_block_id
                   JOIN organizations holder ON holder.id = b.current_holder_id
                   JOIN organizations coop ON coop.id = b.cooperative_id
                   ORDER BY b.created_at DESC"""
            )
            self.json(200, {"batches": rows(cur)})

    def create_batch(self):
        user = self.auth({"cooperative", "regulator", "admin"})
        if not user:
            return
        body = self.read_json()
        if body is None:
            return
        required = ["batch_code", "mining_block_id", "gross_weight_g", "purity_pct", "extraction_date"]
        if any(not body.get(k) for k in required):
            return self.error(400, "Missing required batch fields")
        with db() as conn:
            block = conn.execute("SELECT * FROM mining_blocks WHERE id = ?", (body["mining_block_id"],)).fetchone()
            if not block:
                return self.error(404, "Mining block not found")
            org_id = user["organization_id"] if user["role"] == "cooperative" else block["cooperative_id"]
            cur = conn.execute(
                """INSERT INTO gold_batches
                   (batch_code, mining_block_id, cooperative_id, current_holder_id, status, gross_weight_g, purity_pct, fair_trade_premium_pct, extraction_date)
                   VALUES (?, ?, ?, ?, 'allocated', ?, ?, ?, ?)""",
                (
                    body["batch_code"], body["mining_block_id"], org_id, org_id,
                    float(body["gross_weight_g"]), float(body["purity_pct"]),
                    float(body.get("fair_trade_premium_pct", 7.5)), body["extraction_date"],
                ),
            )
            batch_id = cur.lastrowid
            prev = latest_previous_hash(conn, batch_id)
            h = event_hash(batch_id, org_id, "ore_allocated", "New cooperative allocation registered.", prev)
            conn.execute(
                """INSERT INTO ledger_events
                   (batch_id, actor_org_id, event_type, location_lat, location_lng, notes, event_hash, previous_hash)
                   VALUES (?, ?, 'ore_allocated', ?, ?, ?, ?, ?)""",
                (batch_id, org_id, block["latitude"], block["longitude"], "New cooperative allocation registered.", h, prev),
            )
            audit_log(conn, user, "batch.create", self.client_address[0], {"batch_id": batch_id})
            self.json(201, {"id": batch_id, "message": "Batch registered and ledger event appended"})

    def escrows(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            cur = conn.execute(
                """SELECT e.*, b.batch_code, buyer.name buyer, seller.name seller
                   FROM escrows e
                   JOIN gold_batches b ON b.id = e.batch_id
                   JOIN organizations buyer ON buyer.id = e.buyer_id
                   JOIN organizations seller ON seller.id = e.seller_id
                   ORDER BY datetime(e.created_at) DESC"""
            )
            self.json(200, {"escrows": rows(cur)})

    def release_escrow(self, path):
        user = self.auth({"regulator", "buyer", "admin"})
        if not user:
            return
        escrow_id = int(path.split("/")[3])
        with db() as conn:
            escrow = conn.execute("SELECT * FROM escrows WHERE id = ?", (escrow_id,)).fetchone()
            if not escrow:
                return self.error(404, "Escrow not found")
            if escrow["status"] == "released":
                return self.error(409, "Escrow already released")
            conn.execute("UPDATE escrows SET status = 'released', released_at = CURRENT_TIMESTAMP WHERE id = ?", (escrow_id,))
            prev = latest_previous_hash(conn, escrow["batch_id"])
            h = event_hash(escrow["batch_id"], user["organization_id"], "escrow_released", "Escrow released after milestone review.", prev)
            conn.execute(
                "INSERT INTO ledger_events (batch_id, actor_org_id, event_type, notes, event_hash, previous_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (escrow["batch_id"], user["organization_id"], "escrow_released", "Escrow released after milestone review.", h, prev),
            )
            audit_log(conn, user, "escrow.release", self.client_address[0], {"escrow_id": escrow_id})
            self.json(200, {"message": "Escrow released and ledger event appended"})

    def mining_blocks(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            cur = conn.execute(
                """SELECT mb.*, organizations.name cooperative
                   FROM mining_blocks mb JOIN organizations ON organizations.id = mb.cooperative_id
                   ORDER BY mb.district, mb.block_code"""
            )
            self.json(200, {"blocks": rows(cur)})

    def audits(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            cur = conn.execute(
                """SELECT a.*, b.batch_code, o.name auditor
                   FROM ethical_audits a
                   JOIN gold_batches b ON b.id = a.batch_id
                   JOIN organizations o ON o.id = a.auditor_id
                   ORDER BY datetime(a.created_at) DESC"""
            )
            self.json(200, {"audits": rows(cur)})

    def create_audit(self):
        user = self.auth({"auditor", "regulator", "admin"})
        if not user:
            return
        body = self.read_json()
        if body is None:
            return
        with db() as conn:
            conn.execute(
                """INSERT INTO ethical_audits (batch_id, auditor_id, audit_type, score, finding, corrective_action)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    body.get("batch_id"), user["organization_id"], body.get("audit_type", "chain_of_custody"),
                    int(body.get("score", 0)), body.get("finding", ""), body.get("corrective_action"),
                ),
            )
            audit_log(conn, user, "audit.create", self.client_address[0], {"batch_id": body.get("batch_id")})
            self.json(201, {"message": "Audit recorded"})

    def prices(self):
        user = self.auth()
        if not user:
            return
        with db() as conn:
            price_rows = rows(conn.execute("SELECT * FROM gold_prices ORDER BY datetime(captured_at)"))
            latest = price_rows[-1] if price_rows else None
            batches = rows(conn.execute(
                """SELECT batch_code, gross_weight_g, purity_pct, fair_trade_premium_pct,
                          ROUND(gross_weight_g * purity_pct / 100, 2) fine_grams
                   FROM gold_batches ORDER BY created_at DESC"""
            ))
            if latest:
                for batch in batches:
                    base = batch["fine_grams"] * latest["price_usd_per_gram"]
                    batch["spot_value_usd"] = round(base, 2)
                    batch["fair_trade_value_usd"] = round(base * (1 + batch["fair_trade_premium_pct"] / 100), 2)
            self.json(200, {"prices": price_rows, "valuations": batches})


def rows_from(sqlite_rows):
    return [dict(row) for row in sqlite_rows]


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Karamoja GoldTrace running on {host}:{port}")
    server.serve_forever()
