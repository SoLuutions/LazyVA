"""
Auto-updater for LazyVA.
Checks remote version.json, downloads signed Windows installer, and triggers silent upgrade.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import threading
from typing import Callable, Optional, Tuple

import requests

from lazyva import __version__

DEFAULT_UPDATE_URL = "https://api.lazyva.app/api/v1/version"


class AutoUpdater:
    """Manages version checking and installer downloads."""

    def __init__(self, check_url: str = DEFAULT_UPDATE_URL):
        self.check_url = check_url
        self.current_version = __version__
        self._is_checking = False

    def check_for_updates(
        self, callback: Optional[Callable[[bool, Optional[dict], str], None]] = None
    ) -> None:
        """Asynchronously checks for new updates."""
        if self._is_checking:
            return
        self._is_checking = True

        def _worker():
            try:
                resp = requests.get(self.check_url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    latest_ver = data.get("version", "1.0.0")
                    is_newer = self._compare_versions(latest_ver, self.current_version) > 0
                    msg = (
                        f"New version {latest_ver} is available!"
                        if is_newer
                        else "LazyVA is up to date."
                    )
                    if callback:
                        callback(is_newer, data if is_newer else None, msg)
                else:
                    if callback:
                        callback(False, None, "Could not check for updates.")
            except Exception as e:
                if callback:
                    callback(False, None, f"Update check error: {e}")
            finally:
                self._is_checking = False

        threading.Thread(target=_worker, daemon=True).start()

    def download_and_install(
        self,
        download_url: str,
        expected_sha256: Optional[str] = None,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> Tuple[bool, str]:
        """Downloads latest installer and launches Inno Setup installer."""
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "LazyVA_Update_Setup.exe")

            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_len = int(r.headers.get("content-length", 0))
                downloaded = 0
                hasher = hashlib.sha256()

                with open(installer_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            downloaded += len(chunk)
                            if total_len > 0 and progress_cb:
                                progress_cb(downloaded / total_len)

            # Verify checksum if provided
            if expected_sha256:
                actual_hash = hasher.hexdigest().lower()
                if actual_hash != expected_sha256.lower():
                    return False, "Checksum verification failed. Installer corrupted."

            # Launch Windows installer with /SILENT flag and exit
            if sys.platform == "win32":
                subprocess.Popen([installer_path, "/SILENT", "/CLOSEAPPLICATIONS"])
                sys.exit(0)
            else:
                return True, f"Downloaded to {installer_path}"
        except Exception as e:
            return False, f"Failed to download update: {e}"

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        def parse(v):
            return [int(x) for x in v.split(".") if x.isdigit()]
        p1, p2 = parse(v1), parse(v2)
        return (p1 > p2) - (p1 < p2)
