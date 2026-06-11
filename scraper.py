import os
import re
import time
import random
from playwright.sync_api import sync_playwright
import playwright_stealth
from urllib.parse import urlparse

# --- CONFIGURATION ---
BASE_URL = "https://www.abc.ie" # change this as needed
SEARCH_PATH = "/clothes/" # change this as needed
LISTING_PATTERN = "/for-sale/"

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

def run_scraper(category):
    with sync_playwright() as p:
        # Launch browser once
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        apply_stealth(page)

        # 1. Go to the category/model page
        target_url = f"{BASE_URL}{SEARCH_PATH}{category}"
        print(f"Opening: {target_url}")
        page.goto(target_url)

        # Pause for manual human verification
        print("Waiting for manual Captcha/Cookie clearance (8 seconds)...")
        time.sleep(8) 

        try:
            # Wait for listings to appear
            page.wait_for_selector(f'a[href*="{LISTING_PATTERN}"]', timeout=15000)
            elements = page.query_selector_all(f'a[href*="{LISTING_PATTERN}"]')
            
            # Get unique links only
            links = []
            for e in elements:
                href = e.get_attribute('href')
                if href and href not in links:
                    links.append(href)
            
            # Process first 5 unique links
            for link in links[:5]:
                full_url = link if "http" in link else f"{BASE_URL}{link}"
                
                # FIX: Spawn a clean, separate page instance instead of moving back/forward
                detail_page = context.new_page()
                apply_stealth(detail_page)
                
                try:
                    detail_page.goto(full_url, timeout=30000)
                    detail_page.wait_for_load_state("networkidle")
                    
                    # Ensure title generation has an automated safe layout string fallback
                    raw_title = detail_page.title()
                    title = slugify(raw_title) if slugify(raw_title) else f"item_{int(time.time())}"
                    
                    if not os.path.exists(title):
                        os.makedirs(title)

                    print(f"Downloading images for: {title}")
                    detail_page.mouse.wheel(0, 500)
                    time.sleep(2)

                    imgs = detail_page.query_selector_all('img')
                    count = 1
                    for img in imgs:
                        src = img.get_attribute('src')
                        if src and "http" in src and any(k in src.lower() for k in ["photos", "images", "media"]):
                            try:
                                ext = os.path.splitext(urlparse(src).path)[1] or ".webp"
                                response = detail_page.request.get(src)
                                with open(f"{title}/{count}{ext}", "wb") as f:
                                    f.write(response.body())
                                count += 1
                            except:
                                continue
                                
                    print(f"Finished. Saved {count-1} images.")
                
                except Exception as loop_error:
                    print(f"Skipping listing due to runtime link exception: {loop_error}")
                
                finally:
                    # Explicitly dispose of the tab to release background memory contexts
                    detail_page.close()
                
                time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"Error encountered: {e}")
            page.pause() # Opens debugger if something goes wrong

        browser.close()

if __name__ == "__main__":
    run_scraper("Volkswagen")
