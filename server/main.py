"""
LazyVA SaaS Licensing & Payment Webhook Server.
FastAPI application handling license activations, machine validations, auto-updates,
and automated payment webhook processing (PayMongo for GCash/Maya and Lemon Squeezy).
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# Configuration & Secrets
SECRET_KEY = os.environ.get("LAZYVA_SECRET_KEY", "LAZYVA_SECURE_ENTITLEMENT_SALT_V1_2026")
PAYMONGO_WEBHOOK_SECRET = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
LEMONSQUEEZY_WEBHOOK_SECRET = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "lazyva_saas.db")

app = FastAPI(
    title="LazyVA SaaS API",
    description="Licensing, activation, updates, and payment webhooks for LazyVA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Database Initialization (SQLite Local / Fallback) ─────────────────────────
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id TEXT PRIMARY KEY,
            license_key TEXT UNIQUE NOT NULL,
            email TEXT,
            plan TEXT NOT NULL,
            max_activations INTEGER DEFAULT 2,
            status TEXT DEFAULT 'active',
            created_at REAL,
            expires_at REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id TEXT PRIMARY KEY,
            license_key TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            app_version TEXT,
            activated_at REAL,
            last_seen REAL,
            UNIQUE(license_key, machine_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ── Schemas ───────────────────────────────────────────────────────────────────
class ActivationRequest(BaseModel):
    license_key: str
    machine_id: str
    app_version: Optional[str] = "1.0.0"


class ValidationRequest(BaseModel):
    license_key: str
    machine_id: str


class ManualLicenseIssue(BaseModel):
    email: str
    plan: str = "lifetime"  # 'pro', 'lifetime'
    max_activations: int = 2
    days_valid: Optional[int] = None



# ── Token Helper ──────────────────────────────────────────────────────────────
def generate_license_key(plan_prefix: str = "PRO") -> str:
    """Generates a key like LVA-PRO-98X21-A89BC-44F21"""
    seg1 = secrets.token_hex(2).upper() + secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    seg2 = secrets.token_hex(2).upper() + secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    seg3 = secrets.token_hex(2).upper() + secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    return f"LVA-{plan_prefix}-{seg1}-{seg2}-{seg3}"


def sign_payload(payload: Dict[str, Any]) -> str:
    """Signs payload with HMAC-SHA256 and returns base64.signature"""
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw_json, hashlib.sha256).hexdigest()
    b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8")
    return f"{b64}.{sig}"


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "ok", "app": "LazyVA SaaS Server", "version": "1.0.0"}


@app.post("/api/v1/license/activate")
def activate_license(req: ActivationRequest):
    """Binds a license key to a machine HWID and issues a signed offline token."""
    key = req.license_key.strip().upper()
    mid = req.machine_id.strip()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Query license
    cur.execute("SELECT * FROM licenses WHERE license_key = ?", (key,))
    lic = cur.fetchone()

    if not lic:
        conn.close()
        raise HTTPException(status_code=404, detail="License key not found.")

    if lic["status"] != "active":
        conn.close()
        raise HTTPException(status_code=403, detail=f"License is currently {lic['status']}.")

    # Check expiration
    now = time.time()
    if lic["expires_at"] and lic["expires_at"] < now:
        conn.close()
        raise HTTPException(status_code=403, detail="License has expired. Please renew.")

    # Check existing activations
    cur.execute("SELECT * FROM activations WHERE license_key = ?", (key,))
    activations = cur.fetchall()

    is_already_active = any(a["machine_id"] == mid for a in activations)
    if not is_already_active:
        if len(activations) >= lic["max_activations"]:
            conn.close()
            raise HTTPException(
                status_code=403,
                detail=f"Activation limit reached ({lic['max_activations']} device limit). Please deactivate another device first.",
            )

        # Record activation
        cur.execute(
            """
            INSERT OR REPLACE INTO activations (id, license_key, machine_id, app_version, activated_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (secrets.token_hex(16), key, mid, req.app_version, now, now),
        )
        conn.commit()
    else:
        # Update last seen
        cur.execute(
            "UPDATE activations SET last_seen = ?, app_version = ? WHERE license_key = ? AND machine_id = ?",
            (now, req.app_version, key, mid),
        )
        conn.commit()

    conn.close()

    # Issue signed entitlement payload
    payload = {
        "license_key": key,
        "machine_id": mid,
        "plan": lic["plan"],
        "expires_at": lic["expires_at"],
        "issued_at": now,
    }
    signed_token = sign_payload(payload)

    return {
        "success": True,
        "token": signed_token,
        "plan": lic["plan"],
        "expires_at": lic["expires_at"],
        "message": "Activation successful.",
    }


@app.post("/api/v1/license/validate")
def validate_license(req: ValidationRequest):
    """Validates that a machine is an authorized device for this license."""
    key = req.license_key.strip().upper()
    mid = req.machine_id.strip()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM licenses WHERE license_key = ?", (key,))
    lic = cur.fetchone()

    if not lic or lic["status"] != "active":
        conn.close()
        return {"valid": False, "message": "License inactive or not found."}

    now = time.time()
    if lic["expires_at"] and lic["expires_at"] < now:
        conn.close()
        return {"valid": False, "message": "License has expired."}

    cur.execute("SELECT * FROM activations WHERE license_key = ? AND machine_id = ?", (key, mid))
    act = cur.fetchone()
    if not act:
        conn.close()
        return {"valid": False, "message": "Device not registered for this license."}

    # Refresh last seen
    cur.execute("UPDATE activations SET last_seen = ? WHERE license_key = ? AND machine_id = ?", (now, key, mid))
    conn.commit()
    conn.close()

    payload = {
        "license_key": key,
        "machine_id": mid,
        "plan": lic["plan"],
        "expires_at": lic["expires_at"],
        "issued_at": now,
    }
    return {
        "valid": True,
        "token": sign_payload(payload),
        "plan": lic["plan"],
    }


@app.post("/api/v1/license/deactivate")
def deactivate_license(req: ValidationRequest):
    """Unbinds a device from a license."""
    key = req.license_key.strip().upper()
    mid = req.machine_id.strip()

    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM activations WHERE license_key = ? AND machine_id = ?", (key, mid))
    conn.commit()
    conn.close()

    return {"success": True, "message": "Device deactivated."}


@app.get("/api/v1/version")
def get_version_info():
    """Endpoint checked by client auto-updater."""
    return {
        "version": "1.0.0",
        "release_date": "2026-10-26",
        "notes": "Initial SaaS release of LazyVA. Includes Natural Bezier Mouse Glide, Smart Pomodoro Breaks, and Windows Power Keep-Alive.",
        "download_url": "https://releases.lazyva.app/LazyVA_Setup_v1.0.0.exe",
        "sha256": None,
    }


# ── Payment Webhooks ──────────────────────────────────────────────────────────
@app.post("/api/v1/webhooks/paymongo")
async def paymongo_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handles PayMongo checkout webhooks for Philippine payments (GCash, Maya, Cards).
    Automatically creates license and triggers delivery.
    """
    body = await request.body()
    data = json.loads(body.decode("utf-8"))

    event_type = data.get("data", {}).get("attributes", {}).get("type")
    # Listen for successful payment
    if event_type in ("checkout_session.payment.paid", "payment.paid"):
        payment_attr = data["data"]["attributes"]["data"]["attributes"]
        email = payment_attr.get("billing", {}).get("email") or "customer@example.com"
        amount = payment_attr.get("amount", 0) / 100.0

        # Generate lifetime or pro key
        new_key = generate_license_key(plan_prefix="PRO")

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO licenses (id, license_key, email, plan, max_activations, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (secrets.token_hex(16), new_key, email, "lifetime", 2, "active", time.time(), None),
        )
        conn.commit()
        conn.close()

        print(f"[PayMongo Webhook] Payment of PHP {amount} received for {email}. Generated key: {new_key}")
        # Note: In production, send license key via email here

    return {"status": "received"}


@app.post("/api/v1/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request):
    """Handles Lemon Squeezy order webhooks for international card/PayPal buyers."""
    body = await request.body()
    data = json.loads(body.decode("utf-8"))

    event_name = data.get("meta", {}).get("event_name")
    if event_name == "order_created":
        order_data = data.get("data", {}).get("attributes", {})
        email = order_data.get("user_email")
        new_key = generate_license_key(plan_prefix="PRO")

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO licenses (id, license_key, email, plan, max_activations, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (secrets.token_hex(16), new_key, email, "lifetime", 2, "active", time.time(), None),
        )
        conn.commit()
        conn.close()

        print(f"[LemonSqueezy Webhook] Order created for {email}. Generated key: {new_key}")

    return {"status": "received"}


# ── Admin License Generator Endpoint ──────────────────────────────────────────
@app.post("/api/v1/admin/generate-license")
def admin_generate_license(req: ManualLicenseIssue, x_admin_secret: str = Header(...)):
    """Allows manual generation of license keys (e.g. for personal GCash buyers)."""
    if x_admin_secret != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    expires_at = None
    if req.days_valid:
        expires_at = time.time() + (req.days_valid * 86400)

    key = generate_license_key(plan_prefix="LIFE" if req.plan == "lifetime" else "PRO")

    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO licenses (id, license_key, email, plan, max_activations, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (secrets.token_hex(16), key, req.email, req.plan, req.max_activations, "active", time.time(), expires_at),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "license_key": key,
        "email": req.email,
        "plan": req.plan,
        "max_activations": req.max_activations,
        "expires_at": expires_at,
    }
