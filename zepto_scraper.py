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


def scrape_zepto_pepe():
	url = "https://www.zeptonow.com/"


	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True, slow_mo=400)
		page = browser.new_page()
		print("Opening Zepto homepage...")
		page.goto(url)
		time.sleep(1)


		# Step 1: Select location
		print("Selecting location...")
		page.wait_for_selector("button[aria-label='Select Location']")
		page.click("button[aria-label='Select Location']")
		time.sleep(2)
		page.wait_for_selector("input[placeholder='Search a new address']")
		page.fill("input[placeholder='Search a new address']", "560012")
		time.sleep(2)
		page.click("div.ck03O3 div.c4ZmYS")
		time.sleep(2)
		page.click("button[data-testid='location-confirm-btn']")
		print("Location set to 560012")
		time.sleep(2)


		# Step 2: Search "pepe"
		print("Searching for 'Pepe Jeans'...")
		page.wait_for_selector("span [data-testid='searchBar']")
		page.click("span [data-testid='searchBar']")
		time.sleep(2)
		page.wait_for_selector("input[placeholder='Search for over 5000 products']")
		page.fill("input[placeholder='Search for over 5000 products']", "pepe")
		time.sleep(2)
		page.click("li[id^='pepe jeans']")
		time.sleep(2)
		print("Search executed")


		# Step 3: Click the first product image
		print("Opening first Pepe Jeans product...")
		page.wait_for_selector("img[alt^='Pepe Jeans']")
		page.click("img[alt^='Pepe Jeans']")
		time.sleep(2)


		# Step 4: Click the "Pepe Jeans" brand link inside product page
		print("Navigating to Pepe Jeans catalogue page...")
		page.wait_for_selector("p.font-medium")
		page.locator("p.font-medium", has_text="Pepe Jeans").click()
		time.sleep(2)
		print("Navigated to Pepe Jeans catalogue page")


		# Step 5: Scroll to load all products
		print("Scrolling to load all products...")
		page.wait_for_selector("div.c5SZXs.ccdFPa", timeout=15000)  # wait for first batch


		collected = {}
		last_card_count = 0
		stable_rounds = 0
		max_stable_rounds = 6
		total_rounds = 0
		max_total_rounds = 120

		# Container-aware scrolling routine
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

			# Opportunistically click any load more buttons
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

			# Periodically ensure last card is fully in view
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


		# Step 6: Collect product info (only names starting with "Pepe")
		print("Collecting product data...")
		cards = page.query_selector_all("div.c5SZXs.ccdFPa")
		for card in cards:
			try:
				name = card.query_selector('div[data-slot-id="ProductName"] span').inner_text().strip() if card.query_selector('div[data-slot-id="ProductName"] span') else "NA"
				if not name.startswith("Pepe"):
					continue  # skip products not starting with "Pepe"

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



		# Step 7: Save CSV
		products = list(collected.values())
		filename = f"zepto_pepe_{date.today().isoformat()}.csv"
		with open(filename, "w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(f, fieldnames=["discount", "name", "unit", "current_price", "original_price"])
			writer.writeheader()
			writer.writerows(products)


		print(f"Scraped {len(products)} unique products. Saved to {filename}")
		browser.close()


if __name__ == "__main__":
	scrape_zepto_pepe()



