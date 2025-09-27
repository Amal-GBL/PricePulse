#!/usr/bin/env python3
import os
from datetime import datetime
import traceback

# Ensure Playwright installs system-wide browsers (important for CI)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

any_failed = False
print(f"[INFO] Starting all scrapers at {datetime.now().isoformat(timespec='seconds')}")

SCRAPERS = [
    ("blinkit", "blinkit_scraper", "scrape_blinkit_pepe"),
    ("instamart", "instamart", "scrape_instamart_pepe"),
    ("zepto", "zepto_scraper", "scrape_zepto_pepe"),
]

# Optional: Save all CSVs in current working directory
OUTPUT_DIR = os.getcwd()
print(f"[INFO] Output CSVs will be saved in: {OUTPUT_DIR}")

for name, module_name, func_name in SCRAPERS:
    try:
        print(f"[RUN] {name} scraper")

        # Import the module dynamically
        module = __import__(module_name)

        # Call the scraper function
        scraper_func = getattr(module, func_name)
        scraper_func()  # Assumes each scraper writes its own CSV

        print(f"[OK] {name} scraper completed")

    except Exception as e:
        any_failed = True
        print(f"[ERROR] {name} scraper failed: {e}")
        traceback.print_exc()

print(f"[INFO] All scrapers finished at {datetime.now().isoformat(timespec='seconds')}")
if any_failed:
    print("[DONE] Completed with errors")
    exit(1)
else:
    print("[DONE] All scrapers completed successfully")
    exit(0)
