#!/usr/bin/env python3
from datetime import datetime

any_failed = False

print(f"[INFO] Starting all scrapers at {datetime.now().isoformat(timespec='seconds')}")

# ------------- Blinkit -------------
try:
    import blinkit_scraper

    print("[RUN] blinkit scraper")
    blinkit_scraper.scrape_blinkit_pepe()  # updated scraper
    print("[OK] blinkit scraper completed")
except Exception as e:
    print(f"[ERROR] blinkit scraper failed: {e}")
    any_failed = True

# ------------- Instamart -------------
try:
    import instamart

    print("[RUN] instamart scraper")
    instamart.scrape_instamart_pepe()  # updated scraper
    print("[OK] instamart scraper completed")
except Exception as e:
    print(f"[ERROR] instamart scraper failed: {e}")
    any_failed = True

# ------------- Zepto -------------
try:
    import zepto_scraper

    print("[RUN] zepto scraper")
    zepto_scraper.scrape_zepto_pepe()  # updated scraper
    print("[OK] zepto scraper completed")
except Exception as e:
    print(f"[ERROR] zepto scraper failed: {e}")
    any_failed = True

if any_failed:
    print("[DONE] Completed with errors")
    exit(1)
else:
    print("[DONE] All scrapers completed successfully")
    exit(0)
