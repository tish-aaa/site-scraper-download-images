import os
import re
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from urllib.parse import urlparse

# --- CONFIGURATION ---
BASE_URL = "https://www.scrapingcourse.com"
TARGET_PATH = "/infinite-scrolling"
PRODUCT_SELECTOR = ".product-item"      # each product card in the grid
IMAGE_PATH_MARKER = "wp-content/uploads"  # confirms it's a real product image, not an icon/logo
MAX_SCROLLS = 15                        # safety limit so it doesn't scroll forever
SCROLL_PAUSE = 2                        # seconds to wait for new products to load
MAX_DOWNLOADS = 20 #edit this to keep a limit on number of downloads

def slugify(text):
    # Removes illegal characters for Windows/Linux file systems
    return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:80]

def apply_stealth(page):
    """Safely applies stealth regardless of library version"""
    try:
        playwright_stealth.stealth_sync(page)
    except AttributeError:
        try:
            playwright_stealth.stealth(page)
        except AttributeError:
            print("Notice: Stealth function not found, continuing...")

def scroll_to_load_all(page):
    """Scrolls to the bottom repeatedly until no new content loads, or MAX_SCROLLS is hit."""
    previous_height = 0
    for i in range(MAX_SCROLLS):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(SCROLL_PAUSE)
        current_height = page.evaluate("document.body.scrollHeight")
        print(f"Scroll {i+1}/{MAX_SCROLLS} — page height: {current_height}")
        if current_height == previous_height:
            print("No more new content loading. Stopping scroll.")
            break
        previous_height = current_height

def run_scraper():
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        target_url = f"{BASE_URL}{TARGET_PATH}"
        print(f"Opening: {target_url}")
        page.goto(target_url)
        page.wait_for_selector(PRODUCT_SELECTOR, timeout=15000)

        # Trigger all lazy-loaded products by scrolling to the bottom repeatedly
        scroll_to_load_all(page)

        try:
            products = page.query_selector_all(PRODUCT_SELECTOR)
            print(f"Found {len(products)} products after scrolling.")

            output_folder = "scraped_products"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            count = 0
            for product in products:
                if MAX_DOWNLOADS is not None and count >= MAX_DOWNLOADS:
                    print(f"Reached MAX_DOWNLOADS limit ({MAX_DOWNLOADS}). Stopping.")
                    break
                img_el = product.query_selector("img")
                if not img_el:
                    continue

                src = img_el.get_attribute("src")
                if not src or IMAGE_PATH_MARKER not in src:
                    continue

                # Try to get a product name for the filename, fall back to a counter
                name_el = product.query_selector(".product-name")
                raw_name = name_el.inner_text() if name_el else f"product_{count}"
                filename = slugify(raw_name) or f"product_{count}"

                try:
                    ext = os.path.splitext(urlparse(src).path)[1] or ".jpg"
                    response = page.request.get(src)
                    with open(f"{output_folder}/{filename}{ext}", "wb") as f:
                        f.write(response.body())
                    count += 1
                    print(f"Saved: {filename}{ext}")
                except Exception as img_error:
                    print(f"Skipping image due to error: {img_error}")
                    continue

            print(f"Finished. Saved {count} images to '{output_folder}/'.")

        except Exception as e:
            print(f"Error encountered: {e}")
            page.pause()  # Opens debugger if something goes wrong

        browser.close()

if __name__ == "__main__":
    run_scraper()