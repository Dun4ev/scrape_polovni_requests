import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Сравнение рынков авто",
    page_icon="📊",
    layout="wide"
)

# --- Data Loading ---
@st.cache_data
def load_data(data_path):
    if not os.path.exists(data_path):
        return None
    df = pd.read_csv(data_path)
    df = df.dropna(subset=["price_eur", "mileage_km", "year", "title"]).copy()
    for col, dtype in {"price_eur": int, "mileage_km": int, "year": int}.items():
        df[col] = df[col].astype(dtype)
    if 'search_group' not in df.columns:
        df['search_group'] = 'Default'
    return df

# --- Helper Functions ---
def get_top_deals(df):
    if df.empty:
        return pd.DataFrame()
    max_km_limit = int(df['mileage_km'].max() + 50000)
    bins = list(range(0, max_km_limit, 50000))
    if not bins:
        return pd.DataFrame()
    labels = [f'{i/1000:,.0f} - {(i+50000)/1000:,.0f} тыс. км' for i in bins[:-1]]
    df['mileage_bin'] = pd.cut(df['mileage_km'], bins=bins, labels=labels, right=False)
    top_deals = df.groupby(['mileage_bin', 'search_group'], observed=False).apply(
        lambda x: x.nsmallest(2, 'price_eur')
    ).reset_index(drop=True)
    return top_deals

# --- Main App ---
DATA_PATH = "data/raw/polovni_automobili.csv"
df = load_data(DATA_PATH)

if df is None:
    st.error(f"Файл с данными не найден по пути: {DATA_PATH}")
    st.info("Пожалуйста, сначала запустите скрипт сбора данных: `python3 src/scrape_polovni_botasaurus.py`")
    st.stop()

# --- Sidebar --- 
st.sidebar.header("Фильтры")
all_groups = sorted(df['search_group'].unique())
selected_groups = st.sidebar.multiselect("Выберите группы для сравнения", all_groups, default=all_groups)
min_year, max_year = int(df['year'].min()), int(df['year'].max())
selected_year_range = st.sidebar.slider("Год выпуска", min_year, max_year, (min_year, max_year))
min_km, max_km = int(df['mileage_km'].min()), int(df['mileage_km'].max())
selected_km_range = st.sidebar.slider("Пробег, км", min_km, max_km, (min_km, max_km))

# --- Filtering ---
filtered_df = df[
    (df['search_group'].isin(selected_groups)) &
    (df['year'].between(selected_year_range[0], selected_year_range[1])) &
    (df['mileage_km'].between(selected_km_range[0], selected_km_range[1]))
].copy()

# --- Calculations ---
fig = go.Figure()
if not filtered_df.empty:
    color_map = {group: color for group, color in zip(all_groups, px.colors.qualitative.Plotly)}
    for name, group_df in filtered_df.groupby('search_group'):
        if len(group_df) < 3: continue
        group_color = color_map.get(name, 'grey')
        fig.add_trace(go.Scatter(
            x=group_df['mileage_km'], y=group_df['price_eur'], mode='markers', name=name,
            marker=dict(color=group_color), customdata=group_df['url'], text=group_df['title'],
            hovertemplate="<b>%{text}</b><br>Цена: %{y:,.0f} €<br>Пробег: %{x:,.0f} km<br><i>Кликните для перехода</i><extra></extra>"
        ))
        X = np.c_[np.ones(len(group_df)), group_df["mileage_km"]/1000.0, group_df["year"]]
        y = group_df["price_eur"].values
        try:
            beta = np.linalg.pinv(X.T @ X) @ (X.T @ y)
            mid_year = int(group_df["year"].median())
            km_grid = np.linspace(group_df["mileage_km"].min(), group_df["mileage_km"].max(), 100)
            trend = beta[0] + beta[1]*(km_grid/1000.0) + beta[2]*mid_year
            fig.add_trace(go.Scatter(x=km_grid, y=trend, mode='lines', name=f'Тренд для {name}', line=dict(color=group_color, dash='dash'), hoverinfo='skip'))
        except np.linalg.LinAlgError:
            st.warning(f"Не удалось построить модель для группы '{name}'.")

fig.update_layout(xaxis_title="Пробег, км", yaxis_title="Цена, €", legend_title="Группы поиска", template="plotly_dark", height=650)
top_deals_df = get_top_deals(filtered_df)

# --- Sidebar Export Button ---
st.sidebar.divider()
st.sidebar.subheader("Экспорт")
if st.sidebar.button("Сохранить отчет в HTML"):
    if not filtered_df.empty:
        # 1. Generate Graph HTML
        graph_html = fig.to_html(include_plotlyjs='cdn')
        js_code = '<script>var plot_div = document.getElementsByClassName("plotly-graph-div")[0]; plot_div.on("plotly_click", function(data){if(data.points.length > 0){var point = data.points[0]; var url = point.customdata; if(url){window.open(url, "_blank");}}});</script>'
        graph_html = graph_html.replace('</body>', js_code + '</body>')

        # 2. Generate Table HTML with clickable links and index
        deals_for_html = top_deals_df.copy()
        deals_for_html.index = np.arange(1, len(deals_for_html) + 1) # Create index starting from 1
        deals_for_html.index.name = "№" # Set index column name
        deals_for_html['url'] = deals_for_html['url'].apply(lambda x: f'<a href="{x}" target="_blank">Перейти</a>')
        table_html = deals_for_html.to_html(index=True, justify='left', border=0, classes='deals_table', escape=False, table_id="deals-table")

        # 3. Generate dynamic title
        title_str = f"📊 Сравнительный анализ рынков автомобилей: {', '.join(selected_groups)}"

        # 4. Combine into a single report
        report_html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Аналитический отчет</title>
                <script src="https://cdn.jsdelivr.net/npm/vanilla-js-tablesort@0.1.0/dist/vanilla-js-tablesort.min.js"></script>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #111; color: #eee; margin: 2rem; }}
                    h1, h2 {{ color: #eee; border-bottom: 1px solid #444; padding-bottom: 10px; font-weight: 400; }}
                    h1 {{ font-size: 2.2rem; }}
                    h2 {{ font-size: 1.75rem; }}
                    .deals_table {{ width: 100%; border-collapse: collapse; }}
                    .deals_table th, .deals_table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }}
                    .deals_table th {{ background-color: #222; cursor: pointer; }}
                    .deals_table tr:hover {{ background-color: #2a2a2a; }}
                    .deals_table th.sort-up::after {{ content: " ▲"; }}
                    .deals_table th.sort-down::after {{ content: " ▼"; }}
                    a {{ color: #3498db; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <h1>{title_str}</h1>
                {graph_html}
                <h2>Топ-2 самых дешевых предложения по группам пробега</h2>
                {table_html}
                <script>
                    new Tablesort(document.getElementById('deals-table'));
                </script>
            </body>
        </html>
        """
        
        filename = f"analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"
        filepath = os.path.join("results", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_html)
        
        abs_path = os.path.abspath(filepath)
        st.sidebar.success(f"Отчет сохранен: `{abs_path}`")
    else:
        st.sidebar.warning("Нет данных для сохранения.")

# --- Render Main Page ---
st.title("📊 Сравнительный анализ рынков автомобилей")
st.write(f"Найдено **{len(filtered_df)}** автомобилей по вашим фильтрам.")

if filtered_df.empty:
    st.warning("По заданным критериям не найдено ни одного автомобиля.")
else:
    st.header("Зависимость цены от пробега для выбранных групп")
    st.components.v1.html(fig.to_html(), height=700, scrolling=True) # Display simple figure, not full html

    st.header("⭐ Топ-2 самых дешевых предложения по группам пробега")
    st.write("Поиск самых низких цен в каждом диапазоне пробега.")
    st.dataframe(top_deals_df, use_container_width=True, height=1150, column_config={
        "url": st.column_config.LinkColumn("Ссылка", display_text="Перейти ↗"),
        "search_group": st.column_config.Column("Группа поиска"),
        "mileage_bin": st.column_config.Column("Категория пробега")
    })