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

    app_dist_path = dist_dir / (
        f"{cli_args.name}.exe" if cli_args.onefile else cli_args.name
    )
    app_build_dir = build_dir / cli_args.name
    for output_path in (app_dist_path, app_build_dir):
        try:
            if output_path.is_dir():
                shutil.rmtree(output_path)
            elif output_path.exists():
                output_path.unlink()
        except PermissionError as error:
            print(f"\n[ERROR] Cannot remove previous build output: {output_path}")
            if error.filename:
                print(f"Windows is still using: {error.filename}")
            print(
                "Close any running LazyVA instance, including its system-tray "
                "copy, then run the build again."
            )
            raise SystemExit(1) from None

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
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(build_dir),
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
        print(f"Output files located in: {app_dist_path}")
    else:
        print("\n[ERROR] PyInstaller build failed with exit code:", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
