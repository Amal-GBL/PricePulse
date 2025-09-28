from playwright.sync_api import sync_playwright
from datetime import date
import csv
import re
import time
import random

# --- Free Indian proxies (rotate each run) ---
PROXIES = [
    "http://103.216.82.98:6666",
    "http://103.87.41.11:8080",
    "http://103.141.108.34:8080",
    "http://103.45.96.20:8080",
    "http://103.87.41.2:8080",
]

# --- Utility to clean prices ---
def clean_price(price_str):
    if not price_str or price_str == "NA":
        return "NA"
    price = re.sub(r"[^\d]", "", price_str)
    return price if price else "NA"

# --- Blinkit scraper ---
def scrape_blinkit_pepe():
    url = "https://blinkit.com/dc/?collection_filters=W3siYnJhbmRfaWQiOlsxNjIyOF19XQ%3D%3D&collection_name=Pepe+Jeans+Innerfashion"

    proxy = random.choice(PROXIES)
    print(f"Using proxy: {proxy}")

    with sync_playwright() as p:
        print("Launching browser with proxy...")
        browser = p.chromium.launch(
            headless=False,  # headless=False required for GitHub Actions + xvfb
            proxy={"server": proxy},
        )
        context = browser.new_context(
            geolocation={"latitude": 12.9716, "longitude": 77.5946},  # Bangalore
            locale="en-IN",
            permissions=["geolocation"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # Open homepage to set pincode
            print("Opening Blinkit homepage...")
            page.goto("https://blinkit.com/", timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

            # Attempt to set pincode
            print("Setting pincode to 560012...")
            pin_input_selectors = [
                "input[placeholder*='pincode' i]",
                "input[aria-label*='pincode' i]",
                "input[type='tel']",
                "input[type='text']",
            ]
            pincode_set = False
            for sel in pin_input_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    el.fill("560012")
                    el.press("Enter")
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    pincode_set = True
                    print("Pincode entered.")
                    break

            # Navigate to collection URL
            print(f"Opening URL: {url}")
            page.goto(url, timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Scroll to load products
            print("Scrolling to load products...")
            collected = {}
            last_card_count = 0
            stable_rounds = 0
            max_stable_rounds = 4
            total_rounds = 0
            max_total_rounds = 100

            while total_rounds < max_total_rounds:
                total_rounds += 1
                cards = page.query_selector_all("a[href*='/product/']")
                card_count = len(cards)
                if card_count > last_card_count:
                    stable_rounds = 0
                    last_card_count = card_count
                else:
                    stable_rounds += 1
                if stable_rounds >= max_stable_rounds:
                    break
                # Scroll down a bit
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(0.8)

            # Collect product info
            for card in cards:
                try:
                    name_elem = card.query_selector("div[data-test-id='product-name']") or card.query_selector("h3, h4")
                    name = name_elem.inner_text().strip() if name_elem else "NA"

                    cur_elem = card.query_selector("div[data-test-id='current-price']") or card.query_selector("[class*='price']")
                    current_price = clean_price(cur_elem.inner_text()) if cur_elem else "NA"

                    orig_elem = card.query_selector("div[data-test-id='original-price']") or card.query_selector("[class*='mrp']")
                    original_price = clean_price(orig_elem.inner_text()) if orig_elem else "NA"

                    discount_elem = card.query_selector("div[data-test-id='discount']") or card.query_selector("[class*='discount']")
                    discount = discount_elem.inner_text().strip() if discount_elem else "NA"

                    sizes_elem = card.query_selector("[data-test-id='size']") or card.query_selector("div[class*='size']")
                    sizes = sizes_elem.inner_text().replace("ADD","").strip() if sizes_elem else "NA"

                    collected[name] = {
                        "name": name,
                        "current_price": current_price,
                        "original_price": original_price,
                        "discount": discount,
                        "sizes": sizes
                    }
                except:
                    continue

            # Save CSV
            filename = f"blinkit_pepe_{date.today().isoformat()}.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["name","current_price","original_price","discount","sizes"])
                writer.writeheader()
                writer.writerows(collected.values())

            print(f"Scraped {len(collected)} products. Saved to {filename}")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    scrape_blinkit_pepe()
