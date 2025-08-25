# scrape_polovni_botasaurus.py
# pip install botasaurus botasaurus-requests bs4 lxml pandas numpy
from botasaurus.browser import browser
from botasaurus_driver.driver import Driver
from botasaurus_requests import request as hrequest
from bs4 import BeautifulSoup
import re, time, random, math
import pandas as pd
import numpy as np

BASE = "https://www.polovniautomobili.com"

def parse_cards(html):
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text(" ", strip=True)
    total = None
    m = re.search(r"ukupno\s+(\d+)", txt, flags=re.I)
    if m: total = int(m.group(1))

    cards = []
    for article in soup.select('article.classified'):
        link_element = article.select_one('a[href*="/auto-oglasi/"]')
        if not link_element:
            continue

        href = link_element.get("href") or ""
        if "/auto-oglasi/pretraga" in href:
            continue
        if not href.startswith("http"):
            href = BASE.rstrip("/") + href
        
        title_element = article.select_one('h2 a')
        title = title_element.get_text(strip=True) if title_element else ''

        price_text = article.get('data-price')
        price = None
        if price_text:
            pm = re.search(r"([\d\.]+)", price_text)
            if pm:
                price = int(re.sub(r"[^\d]", "", pm.group(1)))
        
        km = None
        km_element = article.select_one('.setInfo:nth-of-type(2) .top')
        if km_element:
            km_text = km_element.get_text(strip=True)
            km_m = re.search(r"(\d[\d\.\s]*)\s*km", km_text, flags=re.I)
            if km_m: km = int(re.sub(r"[^\d]", "", km_m.group(1)))

        yr = None
        yr_element = article.select_one('.setInfo:nth-of-type(1) .top')
        if yr_element:
            yr_text = yr_element.get_text(strip=True)
            yr_m = re.search(r"\b(20\d{2})", yr_text)
            if yr_m: yr = int(yr_m.group(1))

        # The old model-specific check has been removed to allow any model.
        cards.append({"url": href, "title": title,
                      "price_eur": price, "mileage_km": km, "year": yr})
    return cards, total

@browser(block_images_and_css=True, reuse_driver=True)
def render_page(driver: Driver, url):
    driver.google_get(url)
    driver.wait_for_dom_stable()
    driver.scroll_to_bottom()
    time.sleep(0.8)
    return driver.page_html()

def get_page_html(url, render=False):
    if not render:
        r = hrequest.get(url, headers={"Referer": "https://www.google.com/"}, timeout=30)
        r.raise_for_status()
        return r.text
    else:
        return render_page(url)

def scrape(url, render=False):
    html = get_page_html(url, render=render)
    cards, total = parse_cards(html)
    if total is None:
        print(f"Warning: Could not determine total number of pages for {url}. Scraping only first page.")
        pages = 1
    else:
        pages = math.ceil(total / 25)
    
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    def set_q(url, k, v):
        u = urlparse(url); q = parse_qs(u.query); q[k] = [str(v)]
        return urlunparse((u.scheme,u.netloc,u.path,u.params,urlencode(q, doseq=True),u.fragment))

    for p in range(2, pages + 1):
        page_url = set_q(url, "page", p)
        print(f"  - Scraping page {p}/{pages}...")
        try:
            h = get_page_html(page_url, render=render)
            c, _ = parse_cards(h)
            cards += c
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"    Error scraping page {page_url}: {e}")
            continue
            
    df = pd.DataFrame(cards).drop_duplicates(subset=["url"])
    df = df.dropna(subset=["price_eur","mileage_km","year"])
    df['source'] = 'polovni_automobili' # Add source identifier
    return df

if __name__ == "__main__":
    SEARCH_QUERIES = {
        "Volvo XC60": ("https://www.polovniautomobili.com/auto-oglasi/pretraga?brand=volvo&model%5B%5D=xc60&year_from=2019&year_to=&showOldNew=all&without_price=1"),
        "BMW X5": ("https://www.polovniautomobili.com/auto-oglasi/pretraga?brand=bmw&model%5B%5D=x5&brand2=&price_from=&price_to=&year_from=2019&year_to=&flywheel=&atest=&door_num=&submit_1=&without_price=1&date_limit=&showOldNew=all&modeltxt=&engine_volume_from=&engine_volume_to=&power_from=&power_to=&mileage_from=&mileage_to=&emission_class=&seat_num=&wheel_side=&registration=&country=&country_origin=&city=&registration_price=&page=&sort="),
        "Volvo XC90": ("https://www.polovniautomobili.com/auto-oglasi/pretraga?brand=volvo&model%5B%5D=xc90&year_from=2019&year_to=&showOldNew=all&without_price=1")
    }

    all_dfs = []
    for query_name, url in SEARCH_QUERIES.items():
        print(f"Scraping query: '{query_name}'...")
        df = scrape(url, render=False)  # если начнутся блоки → True
        df['search_group'] = query_name # Add a column to identify the source query
        all_dfs.append(df)
        print(f"Found {len(df)} results for '{query_name}'.")

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        print(f"\nTotal results from all queries: {len(final_df)}")
        print(final_df.head())
        final_df.to_csv('data/raw/polovni_automobili.csv', index=False)
        print("\nData saved to data/raw/polovni_automobili.csv")
    else:
        print("No data was scraped.")