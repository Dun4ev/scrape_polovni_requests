import os
import pandas as pd
import streamlit as st
import duckdb

DB_FILE = "data/cars.duckdb"
TABLE_NAME = "cars"

@st.cache_data(ttl=3600) # Кешируем результат на 1 час
def load_all_data(force_reload: bool = False):
    """
    Загружает данные из Parquet в постоянную базу данных DuckDB.
    Если таблица в БД уже существует, читает из нее, если не указана принудительная перезагрузка.
    """
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    con = duckdb.connect(database=DB_FILE, read_only=False)

    try:
        if force_reload:
            con.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
            st.info(f"Принудительное обновление: таблица '{TABLE_NAME}' будет создана заново.")

        # Проверяем, существует ли таблица
        tables = con.execute(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{TABLE_NAME}'").fetchall()
        
        if not tables:
            st.info(f"Таблица '{TABLE_NAME}' не найдена. Загрузка данных из Parquet файлов...")
            
            parquet_files = [
                "data/raw/polovni_automobili.parquet",
                "data/raw/mobile_de.parquet"
            ]
            
            existing_files = [f for f in parquet_files if os.path.exists(f)]

            for f in parquet_files:
                if not os.path.exists(f):
                    source_name = os.path.basename(f).replace('.parquet', '')
                    st.warning(f"Файл с данными для источника '{source_name}' не найден: {f}")

            if not existing_files:
                st.error("Не найдены Parquet файлы для загрузки.")
                return None

            # Важно: в SQL запросе SELECT должен быть в скобках при использовании CREATE TABLE AS
            read_parquet_query = f"SELECT *, regexp_replace(filename, '.*[\\/]([^\\/]+)\.parquet', '\\1') AS source FROM read_parquet({existing_files})"
            
            try:
                con.execute(f"CREATE TABLE {TABLE_NAME} AS ({read_parquet_query})")
                st.success(f"Данные успешно загружены в таблицу '{TABLE_NAME}' в файле '{DB_FILE}'.")
            except Exception as e:
                st.error(f"Ошибка при создании таблицы из Parquet файлов: {e}")
                return None

        # Читаем данные из постоянной таблицы
        combined_df = con.execute(f"SELECT * FROM {TABLE_NAME}").fetchdf()

    except Exception as e:
        st.error(f"Ошибка при работе с DuckDB: {e}")
        return None
    finally:
        con.close()


    if combined_df.empty:
        st.warning("База данных пуста.")
        return None

    # Обработка данных
    combined_df = combined_df.dropna(subset=["price_eur", "mileage_km", "year", "title"]).copy()
    for col, dtype in {"price_eur": int, "mileage_km": int, "year": int}.items():
        combined_df[col] = combined_df[col].astype(dtype)
    
    if 'search_group' not in combined_df.columns:
        combined_df['search_group'] = 'Default'

    combined_df['comparison_group'] = combined_df['search_group'] + " (" + combined_df['source'] + ")"
    
    return combined_df


def get_car_search_config():
    """Returns the car search configuration."""
    return {
        "polovni_automobili": {
            "Volvo XC60": "https://www.polovniautomobili.com/auto-oglasi/pretraga?brand=volvo&model%5B%5D=xc60&price_from=10000&price_to=20000&year_from=2015&year_to=2019&chassis%5B%5D=4&chassis%5B%5D=20&chassis%5B%5D=21&without_price=1",
            "Audi A4": "https://www.polovniautomobili.com/auto-oglasi/pretraga?brand=audi&model%5B%5D=a4&price_from=10000&price_to=20000&year_from=2015&year_to=2019&chassis%5B%5D=1&chassis%5B%5D=2&chassis%5B%5D=3&without_price=1"
        },
        "mobile_de": {
            "Volvo XC60": "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&ms=25100%3B31%3B%3B&pageNumber=1&ref=dsp&s=Car&sb=rel&vc=Car",
            "Audi A4": "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&ms=1900%3B9%3B%3B&pageNumber=1&ref=dsp&s=Car&sb=rel&vc=Car"
        }
    }