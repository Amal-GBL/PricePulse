# blinkit_scraper.py
from playwright.sync_api import sync_playwright, TimeoutError
from datetime import date
import csv
import re
import time

PINCODE = "560012"
SEARCH_TERM = "pepe"
OUTPUT_CSV = "blinkit_data.csv"


def clean_price(price_str):
    if not price_str:
        return "NA"
    price = re.sub(r"[^\d]", "", price_str)
    return price if price else "NA"


def scrape_blinkit_pepe():
    url_home = "https://blinkit.com/"
    url_collection_fallback = "https://blinkit.com/dc/?collection_filters=W3siYnJhbmRfaWQiOlsxNjIyOF19XQ%3D%3D&collection_name=Pepe+Jeans+Innerfashion"

    with sync_playwright() as p:
        print("Launching headless browser...")
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
            permissions=["geolocation"],
        )

        page = context.new_page()
        collected = {}
        try:
            # 1) Go to homepage
            print("Opening Blinkit homepage...")
            page.goto(url_home, timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

            # 2) Click on the location input
            print("Opening location input...")
            location_input_selectors = [
                'input[name="select-locality"]',
                "input[placeholder*='search delivery location' i]",
                "input.LocationSearchBox__InputSelect-sc-1k8u6a6-0",
            ]
            location_clicked = False
            for sel in location_input_selectors:
                try:
                    page.wait_for_timeout(300)
                    if page.query_selector(sel):
                        print(f"  -> Found location input using selector: {sel}")
                        page.click(sel, timeout=10000)
                        location_clicked = True
                        time.sleep(0.6)
                        break
                except Exception:
                    pass
            if not location_clicked:
                print("  ! Could not find explicit location input; continuing (will fallback).")

            # 3) Type pincode
            typed = False
            for sel in location_input_selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        el.fill(PINCODE)
                        page.keyboard.press("Enter")
                        typed = True
                        print(f"Typed pincode {PINCODE} into {sel}")
                        break
                except Exception:
                    pass
            if not typed:
                # Try a generic text input
                try:
                    generic = page.query_selector("input[type='text']")
                    if generic:
                        generic.click()
                        generic.fill(PINCODE)
                        page.keyboard.press("Enter")
                        typed = True
                        print("Typed pincode into generic input")
                except Exception:
                    pass

            # 4) Click the suggestion that contains the pincode / Bengaluru text
            location_selected = False
            try:
                # Wait for suggestion list to appear
                page.wait_for_timeout(600)
                # Prefer the exact container class the site uses
                suggestion_selector = "div.LocationSearchList__LocationDetailContainer-sc-93rfr7-1"
                if page.query_selector(suggestion_selector):
                    suggestions = page.query_selector_all(suggestion_selector)
                    for s in suggestions:
                        try:
                            txt = (s.inner_text() or "").strip()
                            if "560012" in txt or "Bengaluru" in txt or "Karnataka" in txt:
                                s.click()
                                location_selected = True
                                print("Clicked suggestion matching pincode / Bengaluru.")
                                page.wait_for_load_state("networkidle", timeout=30000)
                                time.sleep(1)
                                break
                        except Exception:
                            pass
                # fallback: any suggestion containing 560012
                if not location_selected:
                    all_suggestions = page.query_selector_all("div")
                    for s in all_suggestions:
                        try:
                            txt = (s.inner_text() or "").strip()
                            if "560012" in txt and "India" in txt:
                                s.click()
                                location_selected = True
                                print("Clicked fallback suggestion containing 560012.")
                                page.wait_for_load_state("networkidle", timeout=30000)
                                time.sleep(1)
                                break
                        except Exception:
                            pass
            except Exception:
                pass

            if not location_selected:
                print("Location suggestion click not confirmed. Continuing (some sites accept pincode without explicit click).")

            # 5) Click on search animation wrapper to focus search (step 5)
            print("Activating search bar...")
            search_anim_sel = "div.SearchBar__AnimationWrapper-sc-16lps2d-1"
            try:
                if page.query_selector(search_anim_sel):
                    page.click(search_anim_sel)
                    time.sleep(0.6)
                else:
                    # fallback: click a generic search wrapper
                    page.click("div[role='search']", timeout=5000) if page.query_selector("div[role='search']") else None
                    time.sleep(0.6)
            except Exception:
                pass

            # 6) Type 'pepe' into the search box (placeholder "Search for atta dal and more")
            search_input_selectors = [
                "input[placeholder*='Search for' i]",
                "input.SearchBarContainer__Input-sc-hl8pft-3",
                "input[aria-label*='Search' i]",
                "input[type='search']",
            ]
            searched = False
            for sel in search_input_selectors:
                try:
                    if page.query_selector(sel):
                        page.click(sel)
                        page.fill(sel, SEARCH_TERM)
                        page.keyboard.press("Enter")
                        print(f"Searched for '{SEARCH_TERM}' using selector: {sel}")
                        page.wait_for_load_state("networkidle", timeout=30000)
                        time.sleep(1.2)
                        searched = True
                        break
                except Exception:
                    pass
            if not searched:
                print("Search input not found; navigating to collection fallback URL.")
                page.goto(url_collection_fallback, timeout=120000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1.2)

            # 7) Click on brand tile 'jeans innerfashion' (span)
            clicked_brand = False
            try:
                # Look for span containing 'jeans innerfashion' (case-insensitive)
                candidates = page.query_selector_all("span")
                for c in candidates:
                    try:
                        txt = (c.inner_text() or "").strip()
                        if "jeans innerfashion" in txt.lower() or "jeans inner fashion" in txt.lower():
                            c.click()
                            page.wait_for_load_state("networkidle", timeout=30000)
                            time.sleep(1)
                            clicked_brand = True
                            print("Clicked brand tile 'jeans innerfashion'.")
                            break
                    except Exception:
                        pass
            except Exception:
                pass

            # If couldn't click brand tile, try to click an element that has 'Pepe' text in search results
            if not clicked_brand:
                try:
                    result = page.query_selector("div:has-text('Pepe')")
                    if result:
                        result.click()
                        page.wait_for_load_state("networkidle", timeout=30000)
                        time.sleep(1)
                        clicked_brand = True
                        print("Clicked a search result containing 'Pepe'.")
                except Exception:
                    pass

            if not clicked_brand:
                print("Couldn't navigate via brand tile/search result; trying fallback collection URL.")
                page.goto(url_collection_fallback, timeout=120000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1.2)

            # 8) Now on brand/catalogue page — scroll until no new products load
            print("Scrolling to load all products (virtualized-aware)...")
            stable_rounds = 0
            max_stable_rounds = 5
            total_rounds = 0
            max_total_rounds = 300
            last_card_count = 0

            def perform_scroll_and_measure():
                result = page.evaluate(
                    """
(() => {
  const container = document.querySelector('#plpContainer') || document.querySelector('div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2') || document.querySelector('main') || document.scrollingElement || document.documentElement || document.body;
  if (!container) return { sh:0, st:0, ch:0 };
  const delta = Math.floor((container.clientHeight || window.innerHeight || 800) * 0.9);
  const nextTop = Math.min((container.scrollTop || 0) + delta, container.scrollHeight || 0);
  container.scrollTop = nextTop;
  return { sh: container.scrollHeight || 0, st: container.scrollTop || 0, ch: container.clientHeight || 0 };
})()
                    """
                )
                # try clicking any "Load more" style buttons
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
                            time.sleep(0.5)
                    except Exception:
                        pass
                return result

            while True:
                total_rounds += 1
                info = perform_scroll_and_measure()
                time.sleep(0.9)

                # Identify card elements — try several candidate selectors
                candidate_selectors_for_cards = [
                    "div[data-test-id='product-card']",
                    "a[href*='/product/']",
                    "div.tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                    "div.c5SZXs.ccdFPa",  # zepto-like fallback
                    "img.tw-h-full.tw-w-full",  # image-based card detection
                ]
                current_cards = []
                for s in candidate_selectors_for_cards:
                    try:
                        elems = page.query_selector_all(s)
                        if elems:
                            current_cards = elems
                            break
                    except Exception:
                        continue

                card_count = len(current_cards) if current_cards else 0
                print(f"Scroll round {total_rounds}: cards visible = {card_count}")

                new_added = 0
                if current_cards:
                    for card in current_cards:
                        try:
                            # parse name
                            name = "NA"
                            # try a set of selectors inside this card
                            name_candidates = [
                                "div.tw-text-300.tw-font-semibold",
                                "[data-test-id='product-name']",
                                "h3",
                                "h4",
                                "span.tw-text-400.tw-font-semibold",
                            ]
                            for nc in name_candidates:
                                try:
                                    el = card.query_selector(nc)
                                    if el:
                                        txt = (el.inner_text() or "").strip()
                                        if txt:
                                            name = txt
                                            break
                                except Exception:
                                    pass
                            # fallback: alt attribute of image inside the card
                            if name == "NA":
                                img = card.query_selector("img")
                                if img:
                                    alt = img.get_attribute("alt") or ""
                                    if alt:
                                        name = alt.strip()

                            if not name or name == "NA":
                                continue

                            # Only keep products that start with 'Pepe' (case-insensitive)
                            if not name.lower().startswith("pepe"):
                                continue

                            # product url
                            product_url = None
                            try:
                                link = card.query_selector("a[href*='/product/']")
                                if link:
                                    href = link.get_attribute("href")
                                    if href:
                                        product_url = href
                            except Exception:
                                pass

                            # prices
                            current_price = "NA"
                            original_price = "NA"
                            discount = "NA"

                            price_candidates = [
                                "[data-test-id='current-price']",
                                "div.tw-text-200.tw-font-semibold",
                                "div[class*='price']",
                                "p[class*='price']",
                            ]
                            for pc in price_candidates:
                                try:
                                    el = card.query_selector(pc)
                                    if el:
                                        current_price = clean_price(el.inner_text().strip())
                                        if current_price != "NA":
                                            break
                                except Exception:
                                    pass

                            orig_candidates = [
                                "[data-test-id='original-price']",
                                "div.tw-text-200.tw-font-regular",
                                "div[class*='mrp']",
                                "p[class*='mrp']",
                            ]
                            for oc in orig_candidates:
                                try:
                                    el = card.query_selector(oc)
                                    if el:
                                        original_price = clean_price(el.inner_text().strip())
                                        if original_price != "NA":
                                            break
                                except Exception:
                                    pass

                            # discount
                            disc_candidates = [
                                "[data-test-id='discount']",
                                "div.tw-text-050",
                                "div[class*='discount']",
                                "span[class*='discount']",
                            ]
                            for dc in disc_candidates:
                                try:
                                    el = card.query_selector(dc)
                                    if el:
                                        txt = (el.inner_text() or "").strip()
                                        if txt:
                                            discount = txt
                                            break
                                except Exception:
                                    pass

                            # image url
                            image_url = "NA"
                            try:
                                img = card.query_selector("img")
                                if img:
                                    src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy-src")
                                    if src:
                                        image_url = src
                            except Exception:
                                pass

                            # Use name+product_url as a key
                            key = (name, product_url)
                            if key not in collected:
                                collected[key] = {
                                    "name": name,
                                    "current_price": current_price,
                                    "original_price": original_price,
                                    "discount": discount,
                                    "image_url": image_url,
                                    "product_url": product_url or "NA",
                                }
                                new_added += 1
                        except Exception:
                            continue

                if new_added:
                    print(f"  + Added {new_added} new products; total unique = {len(collected)}")

                if card_count <= last_card_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                    last_card_count = card_count

                if stable_rounds >= max_stable_rounds:
                    print("No new products appearing after several rounds.")
                    break
                if total_rounds >= max_total_rounds:
                    print("Reached max scroll rounds.")
                    break

            print("Extracting product data...")
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

        products = list(collected.values())
        # Write to CSV
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "current_price", "original_price", "discount", "image_url", "product_url"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)

        print(f"Scraped {len(products)} unique products. Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    scrape_blinkit_pepe()
