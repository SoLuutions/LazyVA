#!/usr/bin/env python3
"""
LazyVA Launcher.
Entry point for running LazyVA from source or launching development instances.
"""

import sys
from pathlib import Path

# Ensure lazyva package is on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from lazyva.app import main

if __name__ == "__main__":
    main()
