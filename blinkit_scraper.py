def scrape_blinkit_pepe(output_file=None):
    url = "https://blinkit.com/dc/?collection_filters=W3siYnJhbmRfaWQiOlsxNjIyOF19XQ%3D%3D&collection_name=Pepe+Jeans+Innerfashion"
    if output_file is None:
        output_file = f"./blinkit_data.csv"

    with sync_playwright() as p:
        print("Launching headless browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
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
            # Set serviceable location
            print("Opening homepage to set location...")
            page.goto("https://blinkit.com/", timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

            print("Attempting to set pincode to 560012...")
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
                    try:
                        el.click()
                        el.fill("560012")
                        el.press("Enter")
                        page.wait_for_load_state("networkidle")
                        time.sleep(1)
                        pincode_set = True
                        print("Pincode entered.")
                        break
                    except Exception:
                        pass

            # Navigate to the collection URL
            print(f"Opening URL: {url}")
            page.goto(url, timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Scroll to load all products
            print("Scrolling to load all products...")
            stable_rounds = 0
            max_stable_rounds = 4
            total_rounds = 0
            max_total_rounds = 300
            last_card_count = 0
            collected = {}

            def parse_card(card):
                name_tag = card.query_selector("div.tw-text-300.tw-font-semibold") or card.query_selector("[data-test-id='product-name']")
                name = (name_tag.inner_text().strip() if name_tag else "NA")
                if name == "NA":
                    return None, None

                cur_tag = card.query_selector("div.tw-text-200.tw-font-semibold") or card.query_selector("[data-test-id='current-price']")
                orig_tag = card.query_selector("div.tw-text-200.tw-font-regular") or card.query_selector("[data-test-id='original-price']")
                cur_price = clean_price(cur_tag.inner_text().strip()) if cur_tag else "NA"
                orig_price = clean_price(orig_tag.inner_text().strip()) if orig_tag else "NA"

                discount_tag = card.query_selector("div.tw-text-050") or card.query_selector("[data-test-id='discount']")
                discount = discount_tag.inner_text().strip() if discount_tag else "NA"

                sizes_tag = card.query_selector("div.tw-font-semibold:has-text('Size')") or card.query_selector("[data-test-id='size']")
                sizes = sizes_tag.inner_text().replace("ADD", "").strip() if sizes_tag else "NA"

                return name, {
                    "name": name,
                    "current_price": cur_price,
                    "original_price": orig_price,
                    "discount": discount,
                    "sizes": sizes,
                }

            while True:
                total_rounds += 1
                cards = page.query_selector_all("div[role='button'].tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start") or page.query_selector_all("div[data-test-id='product-card']") or []
                new_added = 0
                for card in cards:
                    key, data = parse_card(card)
                    if key and key not in collected:
                        collected[key] = data
                        new_added += 1

                card_count = len(cards)
                print(f"Scroll round {total_rounds}: cards visible = {card_count}, new added = {new_added}")

                if card_count <= last_card_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                    last_card_count = card_count

                if stable_rounds >= max_stable_rounds or total_rounds >= max_total_rounds:
                    break

                page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                time.sleep(1)

            # Only save if products are scraped
            products = list(collected.values())
            if products:
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["name", "current_price", "original_price", "discount", "sizes"])
                    writer.writeheader()
                    writer.writerows(products)
                print(f"Scraped {len(products)} unique products. Saved to {output_file}")
            else:
                print("No products scraped. CSV not updated.")

        finally:
            context.close()
            browser.close()
