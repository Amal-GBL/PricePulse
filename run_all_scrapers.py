import subprocess
import sys
from datetime import datetime

# List your scrapers here
SCRAPERS = [
    "instamart_scraper.py",
    "blinkit_scraper.py",
    "bigbasket_scraper.py"
]

def run_scraper(scraper):
    print(f"\n[START] Running {scraper} at {datetime.now()}")
    try:
        # Use subprocess to isolate each scraper
        result = subprocess.run(
            [sys.executable, scraper],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print(f"[SUCCESS] {scraper} finished successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {scraper} failed with return code {e.returncode}")
        print(e.stdout)
        print(e.stderr)
        # Continue to next scraper instead of stopping
        print(f"[CONTINUE] Moving on to next scraper.\n")

def main():
    for scraper in SCRAPERS:
        run_scraper(scraper)

if __name__ == "__main__":
    main()
