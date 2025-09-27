from playwright.sync_api import sync_playwright
import re
import time
import csv


def clean_price(text):
    if not text:
        return "NA"
    return re.sub(r"[^\d]", "", text)


def scrape_instamart_pepe():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.swiggy.com/instamart")

        # --- Step 3: Click on "Search for an area or address"
        page.wait_for_selector('div.sc-aXZVg.jubfzr.tDEYY')
        page.click('div.sc-aXZVg.jubfzr.tDEYY')

        # --- Step 4: Enter pin code
        page.wait_for_selector('input._1wkJd')
        page.fill('input._1wkJd', '560012')
        page.keyboard.press("Enter")
        time.sleep(1)
        page.click('div._11n32 div.sc-aXZVg.gPfbij')

        # --- Step 5: Confirm location
        page.wait_for_selector('button:has-text("Confirm Location")')
        page.click('button:has-text("Confirm Location")')

        # --- Step 6: Click "Re-check your address" if it appears
        time.sleep(2)
        recheck_elements = page.query_selector_all('div.sc-aXZVg.dsXDwT')
        if recheck_elements:
            recheck_elements[0].click(force=True)

        # --- Step 7: Click search bar container and type "pepe"
        search_bar_container = page.wait_for_selector('div._1AaZg')
        search_bar_container.click(force=True)
        time.sleep(0.5)
        search_input = page.wait_for_selector('input[data-testid="search-page-header-search-bar-input"]')
        search_input.fill('pepe')
        time.sleep(1)
        page.click('div.sc-aXZVg.gctPCj._5MSn4', force=True)

        # --- Step 8: Click on brand image (first image)
        page.wait_for_selector('img._16I1D')
        page.click('img._16I1D')

        # --- Step 9: Click "Explore all Pepe Jeans items"
        page.wait_for_selector('span[data-testid="brand-cta-text"]')
        page.click('span[data-testid="brand-cta-text"]')

        # --- Step 10: Card-by-card scrolling
        products = []
        seen_products = set()
        consecutive_no_new = 0
        scroll_pause = 1.0

        while True:
            # Get all product cards currently in DOM
            product_cards = page.query_selector_all('div[data-testid="default_container_ux4"]')
            new_count = 0

            for card in product_cards:
                try:
                    # Scroll this card into view
                    page.evaluate('(el) => el.scrollIntoView({behavior: "smooth", block: "center"})', card)
                    time.sleep(0.3)

                    # Name
                    name_elem = card.query_selector('div.byAowK._1sPB0') or card.query_selector('div.novMV')
                    name = name_elem.inner_text() if name_elem else "NA"
                    if name in seen_products:
                        continue
                    seen_products.add(name)

                    # Unit / size
                    unit_elem = card.query_selector('div[aria-label*="Small"], div[aria-label*="Medium"], div[aria-label*="Large"]')
                    unit = unit_elem.inner_text() if unit_elem else "NA"

                    # Prices and discount
                    current_price_elem = card.query_selector('div[data-testid="item-offer-price"]')
                    original_price_elem = card.query_selector('div[data-testid="item-mrp-price"]')
                    discount_elem = card.query_selector('div[data-testid="offer-text"]')

                    current_price = clean_price(current_price_elem.inner_text()) if current_price_elem else "NA"
                    original_price = clean_price(original_price_elem.inner_text()) if original_price_elem else "NA"
                    discount = discount_elem.inner_text() if discount_elem else "NA"

                    products.append({
                        "name": name,
                        "unit": unit,
                        "current_price": current_price,
                        "original_price": original_price,
                        "discount": discount
                    })
                    new_count += 1
                except:
                    continue

            # Stop after 5 consecutive iterations with no new products
            if new_count == 0:
                consecutive_no_new += 1
            else:
                consecutive_no_new = 0
            if consecutive_no_new >= 5:
                break

            # Scroll a bit more to trigger any lazy loading
            page.evaluate('window.scrollBy(0, 800)')
            time.sleep(scroll_pause)

        # --- Save to CSV
        keys = ["name", "unit", "current_price", "original_price", "discount"]
        with open("instamart_data.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(products)

        print(f"Scraped {len(products)} products.")
        browser.close()


if __name__ == "__main__":
    scrape_instamart_pepe()
