# src/analyze_mobile_de_fields.py
import json
import re
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import pprint

from botasaurus.browser import browser
from bs4 import BeautifulSoup

# Используем существующую функцию рендеринга страницы
from scrape_mobile_de import render_page_mobile_de, find_and_clean_json

def analyze_first_ad(html):
    """
    Парсит HTML, находит первое объявление в данных __INITIAL_STATE__
    и выводит всю информацию о нем в читаемом формате.
    """
    soup = BeautifulSoup(html, "lxml")
    print(f"Анализ страницы с заголовком: \"{soup.title.string}\"")

    script_tag = soup.find("script", string=re.compile(r"window\.__INITIAL_STATE__"))
    if not script_tag:
        print("ОШИБКА: Не удалось найти тег <script> с __INITIAL_STATE__.")
        return

    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(.*)", script_tag.string, re.DOTALL)
    if not match:
        print("ОШИБКА: Не удалось извлечь содержимое из тега <script>.")
        return
    
    raw_js_string = match.group(1)
    json_str = find_and_clean_json(raw_js_string)

    if not json_str:
        print("ОШИБКА: Не удалось найти полный JSON объект.")
        return

    data = json.loads(json_str)

    try:
        results = data['search']['srp']['data']['searchResults']['items']
    except KeyError as e:
        print(f"ОШИБКА: Не удалось найти объявления в JSON. Отсутствует ключ: {e}")
        return

    # Находим первое настоящее объявление
    first_ad = None
    for item in results:
        if item.get("type") in ["ad", "page1Ad", "topAd", "eyecatcherAd"]:
            first_ad = item
            break
    
    if first_ad:
        print("\n--- НАЧАЛО ДАННЫХ ПЕРВОГО ОБЪЯВЛЕНИЯ ---")
        pprint.pprint(first_ad)
        print("--- КОНЕЦ ДАННЫХ ПЕРВОГО ОБЪЯВЛЕНИЯ ---\n")
    else:
        print("Не удалось найти ни одного объявления на странице.")


if __name__ == "__main__":
    # Используем один из ваших поисковых запросов для анализа
    TARGET_URL = "https://suchen.mobile.de/fahrzeuge/search.html?dam=false&fr=2021%3A&isSearchRequest=true&ms=25100%3B40%3B%3B&p=20000%3A41000&ref=srp&refId=ae734efc-d5ac-a8c1-0bad-5187bc37c427&s=Car&vc=Car"

    print(f"Запускаем анализ по URL: {TARGET_URL}")
    
    # Получаем HTML страницы
    html_content = render_page_mobile_de(TARGET_URL)
    
    # Анализируем и выводим данные первого объявления
    analyze_first_ad(html_content)
