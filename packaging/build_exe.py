"""
Build script to compile LazyVA into a standalone Windows executable using PyInstaller.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    build_dir = root / "build"
    icon_ico = root / "assets" / "icon.ico"
    version_file = root / "packaging" / "version_info.txt"

    print("==================================================")
    print("  Building LazyVA Standalone Windows Executable   ")
    print("==================================================")

    import argparse
    parser = argparse.ArgumentParser(description="Build LazyVA standalone executable")
    parser.add_argument("--onefile", action="store_true", help="Build single-file portable executable")
    parser.add_argument("--name", default="LazyVA", help="Binary name")
    cli_args = parser.parse_args()

    # Detect CustomTkinter location to bundle assets
    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent

    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--name", cli_args.name,
        "--onefile" if cli_args.onefile else "--onedir",
        "--icon", str(icon_ico),
        # Bundle assets folder
        "--add-data", f"{root / 'assets'}{sep}assets",
        # Bundle CustomTkinter themes
        "--add-data", f"{ctk_path}{sep}customtkinter",
    ]

    # If building on Linux with uv/custom python, bundle dynamic tcl/tk libraries
    if sys.platform != "win32":
        py_lib = Path(sys.base_prefix) / "lib"
        for so_file in py_lib.glob("libtcl9*.so*"):
            cmd.extend(["--add-binary", f"{so_file}:."])

    cmd.extend([
        # Hidden imports

        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "pystray",
        "--hidden-import", "pynput",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "customtkinter",
        "--hidden-import", "requests",
        # Exclude unnecessary heavy packages to keep executable small
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "IPython",
        "--exclude-module", "unittest",
        "--exclude-module", "pytest",
    ])



    if sys.platform == "win32" and version_file.exists():
        cmd.extend(["--version-file", str(version_file)])

    # Entry point
    cmd.append(str(root / "run.py"))

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root)

    if result.returncode == 0:
        print("\n[SUCCESS] LazyVA build completed successfully!")
        print(f"Output files located in: {dist_dir / 'LazyVA'}")
    else:
        print("\n[ERROR] PyInstaller build failed with exit code:", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
