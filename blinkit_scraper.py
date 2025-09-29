from playwright.sync_api import sync_playwright
from datetime import date
import csv
import re
import time
import os

def clean_price(price_str):
    """Remove currency symbols and commas, return as number or NA."""
    if not price_str or price_str == "NA":
        return "NA"
    price = re.sub(r"[^\d]", "", price_str)
    return price if price else "NA"

def scrape_blinkit_pepe():
    url = "https://blinkit.com/dc/?collection_filters=W3siYnJhbmRfaWQiOlsxNjIyOF19XQ%3D%3D&collection_name=Pepe+Jeans+Innerfashion"
    output_file = f"/app/blinkit_pepe_{date.today().isoformat()}.csv"

    with sync_playwright() as p:
        print("[RUN] blinkit scraper")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 3000},  # Big viewport so more products render
            geolocation={"latitude": 28.6139, "longitude": 77.2090},
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
            # Set location
            page.goto("https://blinkit.com/", timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

            for sel in [
                "input[placeholder*='pincode' i]",
                "input[aria-label*='pincode' i]",
                "input[type='tel']",
                "input[type='text']"
            ]:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    el.fill("560012")
                    el.press("Enter")
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    print("Pincode set.")
                    break

            page.goto(url, timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Save debug screenshot + HTML in case products fail
            debug_screenshot = "/app/blinkit_debug.png"
            debug_html = "/app/blinkit_debug.html"
            page.screenshot(path=debug_screenshot, full_page=True)
            with open(debug_html, "w", encoding="utf-8") as f:
                f.write(page.content())

            # Scroll and collect products
            collected = {}
            stable_rounds = 0
            max_stable_rounds = 4
            total_rounds = 0
            max_total_rounds = 50  # reasonable for container

            def parse_card(card):
                try:
                    name_tag = card.query_selector("div.tw-text-300.tw-font-semibold") or card.query_selector("[data-test-id='product-name']")
                    name = (name_tag.inner_text().strip() if name_tag else "NA")
                    if name == "NA":
                        return None, None

                    cur_tag = card.query_selector("div.tw-text-200.tw-font-semibold") or card.query_selector("[data-test-id='current-price']")
                    orig_tag = card.query_selector("div.tw-text-200.tw-font-regular") or card.query_selector("[data-test-id='original-price']")
                    discount_tag = card.query_selector("div.tw-text-050") or card.query_selector("[data-test-id='discount']")
                    sizes_tag = card.query_selector("div.tw-font-semibold:has-text('Size')") or card.query_selector("[data-test-id='size']")

                    return name, {
                        "name": name,
                        "current_price": clean_price(cur_tag.inner_text()) if cur_tag else "NA",
                        "original_price": clean_price(orig_tag.inner_text()) if orig_tag else "NA",
                        "discount": discount_tag.inner_text().strip() if discount_tag else "NA",
                        "sizes": sizes_tag.inner_text().replace("ADD", "").strip() if sizes_tag else "NA"
                    }
                except:
                    return None, None

            while True:
                total_rounds += 1
                # Scroll container
                page.evaluate("""
() => {
  const el = document.querySelector('#plpContainer') || document.querySelector('div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2') || document.body;
  if (el) el.scrollBy(0, 800);
}
""")
                time.sleep(1)

                cards = page.query_selector_all("div[data-test-id='product-card'], div.tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start")
                new_added = 0
                for card in cards:
                    key, data = parse_card(card)
                    if key and key not in collected:
                        collected[key] = data
                        new_added += 1

                print(f"Scroll round {total_rounds}: cards visible={len(cards)}, new added={new_added}")

                if len(cards) <= stable_rounds:
                    stable_rounds += 1
                else:
                    stable_rounds = 0

                if stable_rounds >= max_stable_rounds or total_rounds >= max_total_rounds:
                    break

            products = list(collected.values())
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "current_price", "original_price", "discount", "sizes"])
                writer.writeheader()
                writer.writerows(products)

            print(f"[OK] Scraped {len(products)} unique products. Saved to {output_file}")
            print(f"[INFO] Debug screenshot: {debug_screenshot}")
            print(f"[INFO] Debug HTML: {debug_html}")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    scrape_blinkit_pepe()
