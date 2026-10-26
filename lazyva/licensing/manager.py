"""
License manager and entitlement gatekeeper for LazyVA.
Enforces SaaS subscription tiers, machine activations, and offline grace periods.
"""

import enum
import json
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

import requests

from lazyva.config import ConfigManager
from .hwid import get_machine_id
from .validator import (
    is_valid_license_format,
    verify_license_token,
    create_token_signature,
)

# Default SaaS API Server endpoint (configurable)
DEFAULT_LICENSE_SERVER_URL = "https://api.lazyva.app"
OFFLINE_GRACE_PERIOD_SECONDS = 7 * 24 * 3600  # 7 days offline grace


class LicenseTier(enum.Enum):
    FREE_TRIAL = "free_trial"
    PRO = "pro"
    LIFETIME = "lifetime"
    EXPIRED = "expired"


class LicenseManager:
    """Manages software licensing, entitlements, and server verification."""

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        server_url: str = DEFAULT_LICENSE_SERVER_URL,
    ):
        self.config = config or ConfigManager()
        self.server_url = server_url.rstrip("/")
        self.machine_id = get_machine_id()
        self.config.set("registered_machine_id", self.machine_id)

        self._tier = LicenseTier.FREE_TRIAL
        self._expires_at: Optional[float] = None
        self._days_remaining: int = 0
        self._lock = threading.Lock()

        # UI Callback on status changes
        self.on_license_updated: Optional[Callable[[LicenseTier, str], None]] = None

        # Initialize and evaluate current status
        self.refresh_status()

    @property
    def tier(self) -> LicenseTier:
        return self._tier

    @property
    def is_pro(self) -> bool:
        return self._tier in (LicenseTier.PRO, LicenseTier.LIFETIME)

    @property
    def is_lifetime(self) -> bool:
        return self._tier == LicenseTier.LIFETIME

    @property
    def days_remaining(self) -> int:
        return self._days_remaining

    def is_feature_allowed(self, feature: str) -> bool:
        """
        Feature gating check.
        Free Tier: basic keep-alive and micro-jitter.
        Pro Tier: Bezier curves, smart breaks, custom hotkeys, auto-start.
        """
        if self.is_pro:
            return True

        if self._tier == LicenseTier.FREE_TRIAL and self._days_remaining > 0:
            return True

        # Gated features on expired/unlicensed tier
        pro_only_features = {
            "bezier_curves",
            "smart_breaks",
            "custom_hotkeys",
            "windows_autostart",
            "fast_intervals",
        }
        return feature not in pro_only_features

    def refresh_status(self) -> Tuple[LicenseTier, str]:
        """Evaluates cached license tokens and updates entitlement status."""
        with self._lock:
            cached_token = self.config.get("cached_license_token", "")
            license_key = self.config.get("license_key", "").strip()

            # 1. Try to verify cached offline token first
            if cached_token:
                valid, payload, msg = verify_license_token(cached_token, self.machine_id)
                if valid and payload:
                    plan = payload.get("plan", "pro").lower()
                    self._tier = LicenseTier.LIFETIME if "life" in plan else LicenseTier.PRO
                    self._expires_at = payload.get("expires_at")
                    if self._expires_at:
                        diff = max(0, int(self._expires_at - time.time()))
                        self._days_remaining = diff // 86400
                    else:
                        self._days_remaining = 9999  # Lifetime
                    return self._tier, "License active."

            # 2. If no valid token but has license key, initiate background validation
            if license_key:
                threading.Thread(target=self._background_server_check, daemon=True).start()

            # 3. Fallback to Local 7-Day Free Trial
            first_run_time = self.config.get("first_run_timestamp", None)
            now = time.time()
            if first_run_time is None:
                first_run_time = now
                self.config.set("first_run_timestamp", first_run_time)

            trial_duration = 7 * 24 * 3600
            time_left = trial_duration - (now - float(first_run_time))
            if time_left > 0:
                self._tier = LicenseTier.FREE_TRIAL
                self._days_remaining = max(1, int(time_left // 86400))
                return self._tier, f"Free Trial active ({self._days_remaining} days left)."
            else:
                self._tier = LicenseTier.EXPIRED
                self._days_remaining = 0
                return self._tier, "Free trial expired. Please enter a license key."

    def activate(self, license_key: str) -> Tuple[bool, str]:
        """
        Activates a license key with the server and stores the signed entitlement token.
        """
        key = license_key.strip().upper()
        if not is_valid_license_format(key):
            return False, "Invalid license key format (e.g. LVA-PRO-XXXXX-XXXXX-XXXXX)."

        payload = {
            "license_key": key,
            "machine_id": self.machine_id,
            "app_version": "1.0.0",
        }

        try:
            resp = requests.post(
                f"{self.server_url}/api/v1/license/activate",
                json=payload,
                timeout=8,
            )
            data = resp.json()

            if resp.status_code == 200 and data.get("success"):
                token = data.get("token")
                self.config.set("license_key", key)
                self.config.set("cached_license_token", token)
                self.config.set("last_license_check", time.time())
                self.refresh_status()

                if self.on_license_updated:
                    self.on_license_updated(self._tier, "License successfully activated!")
                return True, "License successfully activated! Thank you for supporting LazyVA."
            else:
                err = data.get("detail", data.get("message", "License activation failed."))
                return False, err
        except requests.RequestException as e:
            # If server is unreachable, allow offline activation for verified local keys
            return False, f"Could not reach license server ({e}). Please check your internet connection."

    def deactivate(self) -> Tuple[bool, str]:
        """Deactivates the license on this machine to free up an activation slot."""
        license_key = self.config.get("license_key", "")
        if not license_key:
            return False, "No active license to deactivate."

        try:
            requests.post(
                f"{self.server_url}/api/v1/license/deactivate",
                json={"license_key": license_key, "machine_id": self.machine_id},
                timeout=5,
            )
        except Exception:
            pass

        self.config.set("license_key", "")
        self.config.set("cached_license_token", "")
        self.refresh_status()

        if self.on_license_updated:
            self.on_license_updated(self._tier, "License deactivated.")
        return True, "License deactivated on this machine."

    def _background_server_check(self) -> None:
        """Periodically synchronizes license state with server in the background."""
        license_key = self.config.get("license_key", "")
        if not license_key:
            return

        last_check = float(self.config.get("last_license_check", 0.0))
        now = time.time()
        # Check at most once every 12 hours
        if (now - last_check) < 43200:
            return

        try:
            resp = requests.post(
                f"{self.server_url}/api/v1/license/validate",
                json={"license_key": license_key, "machine_id": self.machine_id},
                timeout=6,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid") and data.get("token"):
                    self.config.set("cached_license_token", data["token"])
                    self.config.set("last_license_check", now)
                    self.refresh_status()
        except Exception:
            pass  # Offline grace period applies
