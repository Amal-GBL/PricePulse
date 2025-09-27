from playwright.sync_api import sync_playwright
from datetime import date
import csv
import re
import time


def clean_price(price_str):
   """Remove currency symbols and commas, return as number or NA."""
   if not price_str or price_str == "NA":
       return "NA"
   price = re.sub(r"[^\d]", "", price_str)
   return price if price else "NA"


def scrape_blinkit_pepe():
   url = "https://blinkit.com/dc/?collection_filters=W3siYnJhbmRfaWQiOlsxNjIyOF19XQ%3D%3D&collection_name=Pepe+Jeans+Innerfashion"


   with sync_playwright() as p:
       print("Launching headless browser...")
       browser = p.chromium.launch(headless=True)
       context = browser.new_context(
           geolocation={"latitude": 28.6139, "longitude": 77.2090},  # New Delhi
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
           # First, open homepage to set serviceable location
           print("Opening homepage to set location...")
           page.goto("https://blinkit.com/", timeout=120000)
           # Try to wait for the main content to settle
           page.wait_for_load_state("domcontentloaded")
           time.sleep(1)


           # Try to enter a serviceable pincode if prompted
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


           # If still not set, try opening location changer and input pincode
           if not pincode_set:
               for open_sel in [
                   "button:has-text('Change')",
                   "[data-test-id='change-location']",
                   "[data-testid='change-location']",
                   "button:has-text('Set location')",
               ]:
                   try:
                       btn = page.query_selector(open_sel)
                       if btn:
                           btn.click()
                           time.sleep(0.5)
                           for sel in [
                               "input[placeholder*='pincode' i]",
                               "input[aria-label*='pincode' i]",
                               "input[type='tel']",
                               "input[type='text']",
                           ]:
                               pin = page.query_selector(sel)
                               if pin:
                                   pin.click()
                                   pin.fill("560012")
                                   pin.press("Enter")
                                   page.wait_for_load_state("networkidle")
                                   time.sleep(1)
                                   pincode_set = True
                                   print("Pincode entered via change flow.")
                                   break
                           if pincode_set:
                               break
                   except Exception:
                       pass


           # If there's a detect location button, try clicking it (geolocation is granted)
           if not pincode_set:
               for btn_sel in [
                   "button:has-text('Detect')",
                   "button:has-text('Use current location')",
                   "button:has-text('Detect my location')",
               ]:
                   try:
                       btn = page.query_selector(btn_sel)
                       if btn:
                           btn.click()
                           page.wait_for_load_state("networkidle")
                           time.sleep(1)
                           print("Clicked detect location.")
                           break
                   except Exception:
                       pass


           # Now navigate to the collection URL
           print(f"Opening URL: {url}")
           page.goto(url, timeout=120000)
           page.wait_for_load_state("domcontentloaded")
           # Wait for PLP container if present
           try:
               page.wait_for_selector("#plpContainer, div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2", timeout=15000)
           except Exception:
               pass
           # Dismiss potential modals/popups if present (best-effort; ignore if not found)
           for selector in [
               "button[aria-label='Close']",
               "button[aria-label='close']",
               "button:has-text('No thanks')",
               "button:has-text('Not now')",
           ]:
               try:
                   el = page.query_selector(selector)
                   if el:
                       el.click()
                       time.sleep(0.5)
               except Exception:
                   pass
           # Let the grid render
           time.sleep(3)


           # Scroll to load all products, including inside virtualized/inner scroll containers
           print("Scrolling to load all products (virtualized-aware)...")
           stable_rounds = 0
           max_stable_rounds = 4
           total_rounds = 0
           max_total_rounds = 300
           last_card_count = 0
           # Accumulate unique products across virtualized views
           collected = {}


           def parse_card(card):
               # Prefer product link as unique key; fallback to name
               href = None
               try:
                   link = card.query_selector("a[href*='/product/']")
                   if link:
                       href = link.get_attribute("href") or None
               except Exception:
                   href = None


               # Product name
               name_selectors = [
                   "div.tw-text-300.tw-font-semibold",
                   "[data-test-id='product-name']",
                   "h3, h4",
               ]
               name = "NA"
               for ns in name_selectors:
                   tag = card.query_selector(ns)
                   if tag:
                       txt = (tag.inner_text() or "").strip()
                       if txt:
                           name = txt
                           break


               # Current price
               cur_price_selectors = [
                   "div.tw-text-200.tw-font-semibold",
                   "[data-test-id='current-price']",
                   "[class*='price']",
               ]
               cur_price = "NA"
               for cps in cur_price_selectors:
                   tag = card.query_selector(cps)
                   if tag:
                       cur_price = clean_price((tag.inner_text() or "").strip())
                       if cur_price != "NA":
                           break


               # Original price
               orig_price_selectors = [
                   "div.tw-text-200.tw-font-regular",
                   "[data-test-id='original-price']",
                   "[class*='mrp']",
               ]
               orig_price = "NA"
               for ops in orig_price_selectors:
                   tag = card.query_selector(ops)
                   if tag:
                       orig_price = clean_price((tag.inner_text() or "").strip())
                       if orig_price != "NA":
                           break


               # Discount
               discount_selectors = [
                   "div.tw-text-050",
                   "[data-test-id='discount']",
                   "[class*='discount']",
               ]
               discount = "NA"
               for ds in discount_selectors:
                   tag = card.query_selector(ds)
                   if tag:
                       txt = (tag.inner_text() or "").strip()
                       if txt:
                           discount = txt
                           break


               # Sizes
               sizes = "NA"
               for ss in [
                   "div.tw-font-semibold:has-text('Size')",
                   "[data-test-id='size']",
                   "[class*='size']",
                   "button:has-text('ADD') ~ div",
               ]:
                   tag = card.query_selector(ss)
                   if tag:
                       txt = (tag.inner_text() or "").strip()
                       if txt:
                           sizes = txt
                           break
               if sizes != "NA":
                   sizes = sizes.replace("ADD", "").strip()


               key = href or name
               return key, {
                   "name": name,
                   "current_price": cur_price,
                   "original_price": orig_price,
                   "discount": discount,
                   "sizes": sizes,
               }


           # Helper: get candidate scroll containers and scroll
           def perform_scroll_and_measure():
               result = page.evaluate(
                   """
(() => {
 const plp = document.querySelector('#plpContainer') || document.querySelector('div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2');
 const candidates = [
   plp,
   document.querySelector("div[aria-label='product-grid']"),
   document.querySelector("div[data-test-id='product-grid']"),
   document.querySelector("div.tw-overflow-auto"),
   document.querySelector("main"),
   document.scrollingElement || document.documentElement || document.body,
 ].filter(Boolean);


 let scrolledAny = false;
 let debug = [];
 for (const el of candidates) {
   const sh = el.scrollHeight || 0;
   const ch = el.clientHeight || 0;
   const st = el.scrollTop || 0;
   debug.push({tag: el.tagName, sh, ch, st});
   if (sh > ch) {
     el.scrollTop = sh; // jump to bottom
     scrolledAny = true;
     break;
   }
 }
 const h = document.body ? document.body.scrollHeight : 0;
 return { scrolledAny, pageHeight: h, debug };
})()
                   """
               )
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
                           time.sleep(0.6)
                   except Exception:
                       pass
               return result


           while True:
               total_rounds += 1
               info = perform_scroll_and_measure()
               time.sleep(0.8)


               # Collect any new products currently visible and count cards
               container = page.query_selector("#plpContainer") or page.query_selector("div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2")
               candidate_selectors_for_count = [
                   "div.tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[role='button'].tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[data-test-id='product-card']",
                   "a[href*='/product/']",
               ]
               current_cards = []
               if container:
                   for s in candidate_selectors_for_count:
                       current_cards = container.query_selector_all(s)
                       if current_cards:
                           break
               else:
                   for s in candidate_selectors_for_count:
                       current_cards = page.query_selector_all(s)
                       if current_cards:
                           break
               card_count = len(current_cards) if current_cards else 0
               print(f"Scroll round {total_rounds}: cards visible = {card_count}")


               # Accumulate
               new_added = 0
               if current_cards:
                   for card in current_cards:
                       try:
                           key, data = parse_card(card)
                           if key and key not in collected and data.get("name") != "NA":
                               collected[key] = data
                               new_added += 1
                       except Exception:
                           pass
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


           print("Extracting product data from live DOM and accumulated set...")
           # Final pass to include whatever is currently visible (scoped to container if present)
           final_cards = []
           container = page.query_selector("#plpContainer") or page.query_selector("div.BffPlpFeedContainer__ItemsContainer-sc-12wcdtn-2")
           if container:
               for s in [
                   "div.tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[role='button'].tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[data-test-id='product-card']",
                   "a[href*='/product/']",
               ]:
                   final_cards = container.query_selector_all(s)
                   if final_cards:
                       print(f"Found {len(final_cards)} cards with selector: {s}")
                       break
           else:
               for s in [
                   "div.tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[role='button'].tw-relative.tw-flex.tw-h-full.tw-flex-col.tw-items-start",
                   "div[data-test-id='product-card']",
                   "a[href*='/product/']",
               ]:
                   final_cards = page.query_selector_all(s)
                   if final_cards:
                       print(f"Found {len(final_cards)} cards with selector: {s}")
                       break


           if final_cards:
               for card in final_cards:
                   try:
                       key, data = parse_card(card)
                       if key and key not in collected and data.get("name") != "NA":
                           collected[key] = data
                   except Exception:
                       pass


           # Prepare ordered list for CSV and logging
           products = list(collected.values())
           for idx, item in enumerate(products, start=1):
               print(f"[{idx}] {item['name']} | Current: ₹{item['current_price']} | Original: ₹{item['original_price']} | Discount: {item['discount']} | Sizes: {item['sizes']}")
       finally:
           # Ensure the browser is closed even if an error occurs
           try:
               context.close()
           except Exception:
               pass
           try:
               browser.close()
           except Exception:
               pass


   # Save CSV
   filename = f"blinkit_pepe_{date.today().isoformat()}.csv"
   with open(filename, "w", newline="", encoding="utf-8") as f:
       writer = csv.DictWriter(f, fieldnames=["name", "current_price", "original_price", "discount", "sizes"])
       writer.writeheader()
       writer.writerows(products)


   print(f"Scraped {len(products)} unique products. Saved to {filename}")


if __name__ == "__main__":
   scrape_blinkit_pepe()



