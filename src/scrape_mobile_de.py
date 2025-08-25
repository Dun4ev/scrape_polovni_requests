# scrape_mobile_de.py
import json
import re
import time
import random
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from botasaurus.browser import browser
from botasaurus_driver.driver import Driver
from bs4 import BeautifulSoup

@browser(block_images_and_css=True, reuse_driver=True)
def render_page_mobile_de(driver: Driver, url):
    driver.google_get(url)
    time.sleep(3) # Wait for any dynamic content to load
    return driver.page_html

def find_and_clean_json(text):
    open_braces = 0
    start_index = text.find('{')
    if start_index == -1:
        return None

    for i in range(start_index, len(text)):
        char = text[i]
        if char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
            if open_braces == 0:
                return text[start_index:i+1]
    return None

def parse_from_initial_state(html):
    soup = BeautifulSoup(html, "lxml")
    print(f"Parsing page with title: \"{soup.title.string}\"")

    script_tag = soup.find("script", string=re.compile(r"window\.__INITIAL_STATE__"))
    if not script_tag:
        print("Error: Could not find the __INITIAL_STATE__ script tag.")
        return [], 1

    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(.*)", script_tag.string, re.DOTALL)
    if not match:
        print("Error: Could not extract content from the script tag.")
        return [], 1
    
    raw_js_string = match.group(1)
    json_str = find_and_clean_json(raw_js_string)

    if not json_str:
        print("Error: Could not find a complete JSON object by balancing braces.")
        return [], 1

    data = json.loads(json_str)

    try:
        results = data['search']['srp']['data']['searchResults']['items']
        total_pages = data['search']['srp']['data']['searchResults'].get('numPages', 1)
    except KeyError as e:
        print(f"Error: Could not find search results in JSON. Missing key: {e}")
        return [], 1

    cards = []
    for ad in results:
        # Skip non-ad items like inline advertising slots
        if ad.get("type") not in ["ad", "page1Ad", "topAd", "eyecatcherAd"]:
            continue

        url = ad.get("relativeUrl")
        title = ad.get("title")
        price_data = ad.get("price", {})
        price_str = price_data.get("gross")
        
        attr = ad.get("attr", {})
        mileage_str = attr.get("ml")
        reg_date_str = attr.get("fr")
        
        year = None
        if reg_date_str:
            year_match = re.search(r'\d{2}/(\d{4})', reg_date_str)
            if year_match:
                year = int(year_match.group(1))

        mileage = None
        if mileage_str:
            mileage = int(re.sub(r'[^\d]', '', mileage_str))

        price = None
        if price_str:
            price = int(re.sub(r'[^\d]', '', price_str))

        if all([url, title, price, mileage, year]):
            cards.append({
                "url": "https://suchen.mobile.de" + url,
                "title": title,
                "price_eur": price,
                "mileage_km": mileage,
                "year": year,
                "source": "mobile.de"
            })

    return cards, total_pages

def scrape_mobile_de(url):
    print(f"Scraping initial URL: {url}")
    html = render_page_mobile_de(url)
    cards, total_pages = parse_from_initial_state(html)
    
    print(f"Found {len(cards)} results on the first page. Total pages: {total_pages}.")

    def set_page_param(url, page_num):
        u = urlparse(url)
        q = parse_qs(u.query)
        q['pageNumber'] = [str(page_num)]
        return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q, doseq=True), u.fragment))

    for p in range(2, total_pages + 1):
        page_url = set_page_param(url, p)
        print(f"  - Scraping page {p}/{total_pages}...")
        try:
            h = render_page_mobile_de(page_url)
            c, _ = parse_from_initial_state(h)
            if not c:
                print(f"    No more results found on page {p}. Stopping.")
                break
            cards += c
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"    Error scraping page {page_url}: {e}")
            continue
            
    df = pd.DataFrame(cards)
    if df.empty:
        return df
        
    df = df.dropna().astype({"price_eur": int, "mileage_km": int, "year": int})
    return df

if __name__ == "__main__":
    SEARCH_URL = "https://suchen.mobile.de/fahrzeuge/search.html?dam=false&fr=2019%3A&isSearchRequest=true&ms=25100%3B40%3B%3B&p=20000%3A40000&ref=srp&refId=e6204463-4319-2aa6-e10d-f9b0c1f6815b&s=Car&vc=Car"
    
    print("Starting mobile.de scraper with final JSON logic...")
    
    df = scrape_mobile_de(SEARCH_URL)
    
    if not df.empty:
        output_path = 'data/raw/mobile_de.csv'
        df['search_group'] = 'Volvo XC60'
        print(f"\nTotal results from mobile.de: {len(df)}")
        print(df.head())
        df.to_csv(output_path, index=False)
        print(f"\nData saved to {output_path}")
    else:
        print("No data was scraped from mobile.de.")
