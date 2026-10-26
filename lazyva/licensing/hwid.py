"""
Hardware Identification (HWID) generator.
Computes a stable, anonymous machine fingerprint to bind licenses to specific devices.
"""

import hashlib
import os
import platform
import subprocess
import sys


def get_machine_id() -> str:
    """
    Computes a persistent, anonymous hardware identifier for this machine.
    Returns format: LVA-XXXX-XXXX-XXXX
    """
    components = []

    # 1. OS Architecture and Node Name
    components.append(platform.machine())
    components.append(platform.node())

    if sys.platform == "win32":
        # On Windows, read Cryptography MachineGuid from Registry
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            components.append(str(guid))
            winreg.CloseKey(key)
        except Exception:
            pass

        # Query processor ID
        try:
            output = subprocess.check_output(
                "wmic cpu get ProcessorId /value", shell=True, text=True, timeout=2
            )
            for line in output.splitlines():
                if "ProcessorId=" in line:
                    components.append(line.split("=")[1].strip())
        except Exception:
            pass
    else:
        # Linux fallback: machine-id or DMI UUID
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        components.append(f.read().strip())
                    break
                except Exception:
                    pass

    # Fallback to username & system info if hardware queries failed
    components.append(os.environ.get("USERNAME", os.environ.get("USER", "default")))

    combined = ":".join(components).encode("utf-8")
    digest = hashlib.sha256(combined).hexdigest().upper()

    # Format as LVA-XXXX-XXXX-XXXX
    return f"LVA-{digest[0:4]}-{digest[4:8]}-{digest[8:12]}"
