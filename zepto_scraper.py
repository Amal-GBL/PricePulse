from playwright.sync_api import sync_playwright, TimeoutError
from datetime import date
import csv
import re
import time
import os

def clean_price(price_str):
    if not price_str or price_str == "NA":
        return "NA"
    price = re.sub(r"[^\d]", "", price_str)
    return price if price else "NA"

def scrape_zepto_pepe():
    url = "https://www.zeptonow.com/"
    output_dir = "/tmp"
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # show browser to render JS properly
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(
            viewport={"width": 1280, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )

        try:
            print("Opening Zepto homepage...")
            page.goto(url, wait_until="networkidle")
            time.sleep(2)
            page.screenshot(path=f"{output_dir}/step_homepage.png")

            # Step 1: Select location
            print("Selecting location...")
            try:
                page.wait_for_selector("button[aria-label='Select Location']", timeout=30000)
                page.click("button[aria-label='Select Location']")
                time.sleep(2)
                page.fill("input[placeholder='Search a new address']", "560012")
                time.sleep(2)
                page.click("div.ck03O3 div.c4ZmYS")
                page.click("button[data-testid='location-confirm-btn']")
                print("Location set to 560012")
                time.sleep(2)
                page.screenshot(path=f"{output_dir}/step_location_set.png")
            except TimeoutError:
                print("Location selection failed or timed out. Proceeding anyway...")

            # Step 2: Search "pepe"
            print("Searching for 'Pepe Jeans'...")
            try:
                page.click("span [data-testid='searchBar']")
                time.sleep(2)
                page.fill("input[placeholder='Search for over 5000 products']", "pepe")
                time.sleep(2)
                page.keyboard.press("Enter")
                time.sleep(2)
                page.screenshot(path=f"{output_dir}/step_search.png")
            except TimeoutError:
                print("Search bar interaction failed.")

            # Step 3: Scroll and collect products
            print("Scrolling to load all products...")
            collected = {}
            last_card_count = 0
            stable_rounds = 0
            max_stable_rounds = 6
            total_rounds = 0
            max_total_rounds = 120

            while total_rounds < max_total_rounds:
                total_rounds += 1
                page.evaluate("""
() => {
  const container = document.querySelector('div.c5SZXs.ccdFPa')?.parentElement || document.scrollingElement || document.documentElement;
  if (container) container.scrollBy(0, window.innerHeight * 0.9);
}
                """)
                time.sleep(0.8)

                cards = page.query_selector_all("div.c5SZXs.ccdFPa")
                card_count = len(cards)
                print(f"Scroll round {total_rounds}: cards visible = {card_count}")

                if card_count > last_card_count:
                    stable_rounds = 0
                    last_card_count = card_count
                else:
                    stable_rounds += 1

                if stable_rounds >= max_stable_rounds:
                    print("No new products appearing after several rounds.")
                    break

            page.screenshot(path=f"{output_dir}/step_scrolled.png")
            html_content = page.content()
            with open(f"{output_dir}/step_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)

            # Step 4: Collect product info
            print("Collecting product data...")
            cards = page.query_selector_all("div.c5SZXs.ccdFPa")
            for card in cards:
                try:
                    name = card.query_selector('div[data-slot-id="ProductName"] span').inner_text().strip() if card.query_selector('div[data-slot-id="ProductName"] span') else "NA"
                    if not name.startswith("Pepe"):
                        continue
                    unit = card.query_selector('div[data-slot-id="PackSize"] span').inner_text().strip() if card.query_selector('div[data-slot-id="PackSize"] span') else "1 unit"
                    current_price = clean_price(card.query_selector('div[data-slot-id="Price"] p:first-child').inner_text() if card.query_selector('div[data-slot-id="Price"] p:first-child') else "NA")
                    original_price = clean_price(card.query_selector('div[data-slot-id="Price"] p:last-child').inner_text() if card.query_selector('div[data-slot-id="Price"] p:last-child') else "NA")
                    discount = card.query_selector('div.c5aJJW span:last-child').inner_text().strip() if card.query_selector('div.c5aJJW span:last-child') else "NA"

                    collected[name] = {
                        "discount": discount,
                        "name": name,
                        "unit": unit,
                        "current_price": current_price,
                        "original_price": original_price
                    }
                except Exception as e:
                    print(f"Error collecting a product: {e}")

            # Step 5: Save CSV
            products = list(collected.values())
            filename = os.path.join(output_dir, "zepto_data.csv")
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["discount", "name", "unit", "current_price", "original_price"])
                writer.writeheader()
                writer.writerows(products)

            print(f"Scraped {len(products)} unique products. Saved to {filename}")

        finally:
            browser.close()

if __name__ == "__main__":
    scrape_zepto_pepe()
