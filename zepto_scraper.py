from playwright.sync_api import sync_playwright, TimeoutError
import csv
import re
import time

def clean_price(price_str):
    """Remove currency symbols and commas, return as number or NA."""
    if not price_str or price_str == "NA":
        return "NA"
    price = re.sub(r"[^\d]", "", price_str)
    return price if price else "NA"

def scrape_zepto_pepe(output_file="zepto_data.csv"):
    url = "https://www.zeptonow.com/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )

        print("Opening Zepto homepage...")
        page.goto(url, wait_until="networkidle")
        time.sleep(2)

        # Step 1: Select location
        print("Selecting location...")
        try:
            page.wait_for_selector("button[aria-label='Select Location']", timeout=60000, state="visible")
            page.click("button[aria-label='Select Location']")
            time.sleep(2)
            page.wait_for_selector("input[placeholder='Search a new address']", timeout=30000, state="visible")
            page.fill("input[placeholder='Search a new address']", "560012")
            time.sleep(2)
            page.click("div.ck03O3 div.c4ZmYS")
            time.sleep(2)
            page.click("button[data-testid='location-confirm-btn']")
            print("Location set to 560012")
            time.sleep(2)
        except TimeoutError:
            print("Location selection failed or timed out. Proceeding anyway...")

        # Step 2: Search "pepe"
        print("Searching for 'Pepe Jeans'...")
        try:
            page.wait_for_selector("span [data-testid='searchBar']", timeout=30000)
            page.click("span [data-testid='searchBar']")
            time.sleep(2)
            page.wait_for_selector("input[placeholder='Search for over 5000 products']", timeout=30000)
            page.fill("input[placeholder='Search for over 5000 products']", "pepe")
            time.sleep(2)
            page.click("li[id^='pepe jeans']")
            time.sleep(2)
            print("Search executed")
        except TimeoutError:
            print("Search bar interaction failed.")

        # Step 3: Open first product and navigate to brand catalogue
        print("Opening first Pepe Jeans product...")
        try:
            page.wait_for_selector("img[alt^='Pepe Jeans']", timeout=30000)
            page.click("img[alt^='Pepe Jeans']")
            time.sleep(2)

            print("Navigating to Pepe Jeans catalogue page...")
            page.wait_for_selector("p.font-medium", timeout=30000)
            page.locator("p.font-medium", has_text="Pepe Jeans").click()
            time.sleep(2)
            print("Navigated to Pepe Jeans catalogue page")
        except TimeoutError:
            print("Failed to open product/brand page.")

        # Step 4: Scroll and collect products
        print("Scrolling to load all products...")
        collected = {}
        last_card_count = 0
        stable_rounds = 0
        max_stable_rounds = 6
        total_rounds = 0
        max_total_rounds = 120

        while total_rounds < max_total_rounds:
            total_rounds += 1
            info = page.evaluate(
                """
(() => {
  const containerCandidates = [
    document.querySelector('div.c5SZXs.ccdFPa')?.parentElement,
    document.querySelector("div[aria-label='product-grid']"),
    document.querySelector("div[data-test-id='product-grid']"),
    document.querySelector('main'),
    document.scrollingElement || document.documentElement || document.body,
  ].filter(Boolean);
  const el = containerCandidates[0];
  if (el) {
    const delta = Math.floor((el.clientHeight || window.innerHeight || 800) * 0.9);
    const nextTop = Math.min((el.scrollTop || 0) + delta, el.scrollHeight || 0);
    el.scrollTop = nextTop;
    return { sh: el.scrollHeight || 0, st: el.scrollTop || 0, ch: el.clientHeight || 0 };
  }
  return { sh: 0, st: 0, ch: 0 };
})()
                """
            )
            time.sleep(0.8)

            for sel in [
                "button:has-text('Show more')",
                "button:has-text('Load more')",
                "button:has-text('See more')",
                "[data-test-id='load-more']",
            ]:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(0.4)
                except Exception:
                    pass

            cards = page.query_selector_all("div.c5SZXs.ccdFPa")
            card_count = len(cards)
            print(f"Scroll round {total_rounds}: cards visible = {card_count}, sh={info.get('sh')}, st={info.get('st')}")

            if cards:
                try:
                    page.evaluate("el => el.scrollIntoView({behavior: 'instant', block: 'end'})", cards[-1])
                except Exception:
                    pass

            if card_count > last_card_count:
                stable_rounds = 0
                last_card_count = card_count
            else:
                stable_rounds += 1

            if stable_rounds >= max_stable_rounds:
                print("No new products appearing after several rounds.")
                break

        # Step 5: Collect product info
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

                # Step 6: Save CSV only if products were scraped
        products = list(collected.values())
        if products:  # <-- NEW check
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["discount", "name", "unit", "current_price", "original_price"])
                writer.writeheader()
                writer.writerows(products)
            print(f"Scraped {len(products)} unique products. Saved to {output_file}")
        else:
            print("No products scraped. CSV file not modified.")



if __name__ == "__main__":
    scrape_zepto_pepe()
