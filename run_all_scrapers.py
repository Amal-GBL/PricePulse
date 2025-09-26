#!/usr/bin/env python3
import subprocess
import sys
import os
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_BIN = os.path.join(APP_DIR, 'venv', 'bin')
PYTHON = os.path.join(VENV_BIN, 'python') if os.path.exists(VENV_BIN) else sys.executable

SCRAPERS = [
    ("blinkit", os.path.join(APP_DIR, 'blinkit_scraper.py')),
    ("instamart", os.path.join(APP_DIR, 'instamart.py')),
    ("zepto", os.path.join(APP_DIR, 'zepto_scraper.py')),
]

def run(cmd):
    print(f"[RUN] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=APP_DIR)
    return proc.returncode


def main():
    print(f"[INFO] Starting all scrapers at {datetime.now().isoformat(timespec='seconds')}")

    any_failed = False
    for name, path in SCRAPERS:
        if not os.path.exists(path):
            print(f"[WARN] Skipping {name}: {path} not found")
            continue
        code = run([PYTHON, path])
        if code != 0:
            print(f"[ERROR] {name} scraper failed with exit code {code}")
            any_failed = True
        else:
            print(f"[OK] {name} scraper completed")

    if any_failed:
        print("[DONE] Completed with errors")
        sys.exit(1)
    else:
        print("[DONE] All scrapers completed successfully")
        sys.exit(0)


if __name__ == '__main__':
    main()
