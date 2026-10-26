"""
Cryptographic token and license format validator.
Validates HMAC signed entitlement payloads for offline verification.
"""

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any, Dict, Optional, Tuple

# Public shared client verification secret (pairs with backend signing secret)
# In production, replace with asymmetric RSA/Ed25519 public key or dedicated HMAC secret
CLIENT_SIGNING_SALT = "LAZYVA_SECURE_ENTITLEMENT_SALT_V1_2026"

LICENSE_KEY_REGEX = re.compile(
    r"^LVA-(FREE|PRO|LIFE|TEAM)-[A-Z0-9]{4,5}-[A-Z0-9]{4,5}-[A-Z0-9]{4,5}$",
    re.IGNORECASE,
)


def is_valid_license_format(key: str) -> bool:
    """Checks whether a string matches standard LazyVA license key formatting."""
    if not key:
        return False
    return bool(LICENSE_KEY_REGEX.match(key.strip()))


def create_token_signature(payload_bytes: bytes, secret: str = CLIENT_SIGNING_SALT) -> str:
    """Generates HMAC-SHA256 hex digest for payload."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def sign_payload(payload: Dict[str, Any], secret: str = CLIENT_SIGNING_SALT) -> str:
    """Encodes and signs a dictionary payload into base64.signature format."""
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = create_token_signature(raw_json, secret)
    b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8")
    return f"{b64}.{sig}"



def verify_license_token(token: str, machine_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verifies an offline license token.
    Token format: base64(payload_json).signature_hex
    
    Returns:
        (is_valid, decoded_payload, message)
    """
    if not token or "." not in token:
        return False, None, "Invalid token format."

    parts = token.split(".")
    if len(parts) != 2:
        return False, None, "Malformed token structure."

    b64_payload, signature = parts[0], parts[1]

    try:
        raw_json = base64.urlsafe_b64decode(b64_payload.encode("utf-8"))
        expected_sig = create_token_signature(raw_json)

        if not hmac.compare_digest(signature, expected_sig):
            return False, None, "Token signature mismatch (tampering detected)."

        payload = json.loads(raw_json.decode("utf-8"))

        # Verify machine binding if bound
        token_machine_id = payload.get("machine_id")
        if token_machine_id and token_machine_id != machine_id:
            return False, None, f"License bound to another device ({token_machine_id})."

        # Verify expiration
        expires_at = payload.get("expires_at", 0)
        now = time.time()
        if expires_at and expires_at < now:
            return False, None, "License subscription has expired."

        return True, payload, "License token is valid."
    except Exception as e:
        return False, None, f"Token decode error: {e}"
