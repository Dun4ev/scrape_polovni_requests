import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

from src.data_loader import load_all_data
from src.analysis import get_top_deals, calculate_price_statistics
from src.plotting import create_price_mileage_scatter_plot, create_price_distribution_box_plot
from src.econometrics import create_quantile_lowess_plot, run_hedonic_model

# --- Page Configuration ---
st.set_page_config(
    page_title="Сравнение рынков авто",
    page_icon="📊",
    layout="wide"
)

# --- Data Loading ---
st.sidebar.title("Управление данными")
force_reload = st.sidebar.button("Обновить данные из файлов")
df = load_all_data(force_reload=force_reload)

if df is None:
    st.error("Не найдено ни одного файла с данными в папке `data/raw/`.")
    st.info("Пожалуйста, сначала запустите скрипты сбора данных, например: `python3 src/scrape_polovni_botasaurus.py`")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.title("Фильтры")

all_sources = sorted(df['source'].unique())
selected_sources = st.sidebar.multiselect("Источники данных", all_sources, default=all_sources)

all_groups = sorted(df['search_group'].unique())
selected_groups = st.sidebar.multiselect("Модели для сравнения", all_groups, default=all_groups)

min_year, max_year = int(df['year'].min()), int(df['year'].max())
selected_year_range = st.sidebar.slider("Год выпуска", min_year, max_year, (min_year, max_year))

min_km, max_km = int(df['mileage_km'].min()), int(df['mileage_km'].max())
selected_km_range = st.sidebar.slider("Пробег, км", min_km, max_km, (min_km, max_km))

# --- Filtering ---
filtered_df = df[
    (df['source'].isin(selected_sources)) &
    (df['search_group'].isin(selected_groups)) &
    (df['year'].between(selected_year_range[0], selected_year_range[1])) &
    (df['mileage_km'].between(selected_km_range[0], selected_km_range[1]))
].copy()

# --- Main Page Calculations ---
fig = create_price_mileage_scatter_plot(filtered_df)
top_deals_df = get_top_deals(filtered_df)

# --- Render Main Page ---
st.title("📊 Сравнительный анализ рынков автомобилей")
st.write(f"Найдено **{len(filtered_df)}** автомобилей по вашим фильтрам.")

if filtered_df.empty:
    st.warning("По заданным критериям не найдено ни одного автомобиля.")
else:
    st.header("Зависимость цены от пробега для выбранных групп")
    js_code = '<script>var plot_div = document.getElementsByClassName(\"plotly-graph-div\")[0]; plot_div.on(\"plotly_click\", function(data){if(data.points.length > 0){var point = data.points[0]; var url = point.customdata[0]; if(url){window.open(url, \"_blank\");}}});</script>'
    graph_html = fig.to_html(include_plotlyjs='cdn')
    graph_html = graph_html.replace('</body>', js_code + '</body>')
    st.components.v1.html(graph_html, height=700, scrolling=True)

    if not filtered_df.empty:
        source_counts = filtered_df['source'].value_counts().to_dict()
        summary_parts = [f"**{source}**: {count}" for source, count in source_counts.items()]
        st.write("Количество объявлений по источникам: " + ", ".join(summary_parts))

    st.header("⭐ Топ-2 самых дешевых предложения по группам пробега")
    st.write("Поиск самых низких цен в каждом диапазоне пробега.")
    st.dataframe(top_deals_df, use_container_width=True, height=1150, column_config={
        "url": st.column_config.LinkColumn("Ссылка", display_text="Перейти ↗"),
        "comparison_group": st.column_config.Column("Группа"),
        "mileage_bin": st.column_config.Column("Категория пробега"),
        "source": st.column_config.Column("Источник")
    })

    st.header("📊 Детальное сравнение цен между сайтами")
    st.write("Выберите модель для подробного анализа ценовых распределений по источникам.")

    available_search_groups = sorted(filtered_df['search_group'].unique())
    if available_search_groups:
        selected_model_for_comparison = st.selectbox(
            "Выберите модель для сравнения",
            available_search_groups
        )

        model_comparison_df = filtered_df[
            filtered_df['search_group'] == selected_model_for_comparison
        ].copy()

        if not model_comparison_df.empty:
            st.subheader(f"Статистика цен для {selected_model_for_comparison}")

            price_stats = calculate_price_statistics(model_comparison_df)
            st.dataframe(price_stats.style.format({
                'mean': "€{:,.0f}",
                'median': "€{:,.0f}",
                'std': "€{:,.0f}",
                '25th_percentile': "€{:,.0f}",
                '75th_percentile': "€{:,.0f}"
            }))

            if len(price_stats) > 1:
                medians = price_stats['median'].to_dict()
                sources = list(medians.keys())
                
                if len(sources) == 2:
                    source1, source2 = sources[0], sources[1]
                    median1, median2 = medians[source1], medians[source2]

                    if median1 > 0 and median2 > 0:
                        percentage_diff = ((median2 - median1) / median1) * 100
                        st.write(f"**Разница медианных цен ({source2} относительно {source1}):** {percentage_diff:,.2f}%")
                        if percentage_diff > 0:
                            st.info(f"На сайте {source2} медианная цена на {selected_model_for_comparison} выше на {percentage_diff:,.2f}% по сравнению с {source1}.")
                        elif percentage_diff < 0:
                            st.info(f"На сайте {source2} медианная цена на {selected_model_for_comparison} ниже на {abs(percentage_diff):,.2f}% по сравнению с {source1}.")
                        else:
                            st.info(f"Медианные цены на {selected_model_for_comparison} на обоих сайтах одинаковы.")
                    else:
                        st.warning("Недостаточно данных для расчета процентной разницы медиан.")
                else:
                    st.warning("Для расчета процентной разницы медиан необходимо выбрать данные как минимум с двух источников.")
            else:
                st.warning("Выберите данные как минимум с двух источников для сравнения.")

            st.subheader(f"Распределение цен для {selected_model_for_comparison}")
            fig_box = create_price_distribution_box_plot(model_comparison_df)
            st.plotly_chart(fig_box, use_container_width=True)

            st.header("🔬 Эконометрический анализ")
            st.write("Этот график показывает более сложный анализ зависимости цены от пробега с использованием квантильных коридоров и LOWESS сглаживания.")
            econometrics_fig = create_quantile_lowess_plot(model_comparison_df)
            econometrics_html = econometrics_fig.to_html(include_plotlyjs='cdn')
            # Reuse the js_code defined for the first graph to make points clickable
            econometrics_html = econometrics_html.replace('</body>', js_code + '</body>')
            st.components.v1.html(econometrics_html, height=700, scrolling=True)

            st.subheader("Гедонистическая модель оценки")
            hedonic_model = run_hedonic_model(model_comparison_df)
            if hedonic_model:
                st.write("Результаты регрессионного анализа, который оценивает 'чистую' разницу в ценах между рынками, контролируя пробег и возраст.")
                
                market_coeffs = {k: v for k, v in hedonic_model.params.items() if k.startswith('market_')}
                if market_coeffs:
                    # Also show the reference market
                    if hasattr(hedonic_model, 'reference_market'):
                        st.write(f"*(Базовый рынок для сравнения: **{hedonic_model.reference_market}**)*")

                    for market_var, coeff in market_coeffs.items():
                        # Extract market name from 'market_polovni_automobili'
                        market_name = market_var.replace('market_', '')
                        premium = (np.exp(coeff) - 1) * 100
                        st.metric(label=f"Премия рынка {market_name}", value=f"{premium:.2f}%" )
                
                st.write("Полная таблица с коэффициентами модели:")
                # Parse and display summary tables using st.dataframe for robustness
                summary = hedonic_model.summary()

                st.subheader("Таблица 1: Общая информация о модели")
                table1_data = summary.tables[0].data
                df1_left_data = {row[0].strip(): row[1].strip() for row in table1_data}
                df1_right_data = {row[2].strip(): row[3].strip() for row in table1_data if len(row) > 2 and row[2].strip()}
                df1_left = pd.DataFrame(df1_left_data.items(), columns=['Statistic', 'Value']).set_index('Statistic')
                df1_right = pd.DataFrame(df1_right_data.items(), columns=['Statistic', 'Value']).set_index('Statistic')

                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(df1_left, use_container_width=True)
                with col2:
                    st.dataframe(df1_right, use_container_width=True)

                st.subheader("Таблица 2: Коэффициенты модели")
                table2 = summary.tables[1]
                coeffs_df = pd.DataFrame(table2.data[1:], columns=table2.data[0])
                coeffs_df = coeffs_df.set_index(coeffs_df.columns[0])
                st.dataframe(coeffs_df, use_container_width=True)

                st.subheader("Таблица 3: Дополнительные диагностические тесты")
                table3_data = summary.tables[2].data
                df3_left_data = {row[0].strip(): row[1].strip() for row in table3_data}
                df3_right_data = {row[2].strip(): row[3].strip() for row in table3_data if len(row) > 2 and row[2].strip()}
                df3_left = pd.DataFrame(df3_left_data.items(), columns=['Statistic', 'Value']).set_index('Statistic')
                df3_right = pd.DataFrame(df3_right_data.items(), columns=['Statistic', 'Value']).set_index('Statistic')

                col3, col4 = st.columns(2)
                with col3:
                    st.dataframe(df3_left, use_container_width=True)
                with col4:
                    st.dataframe(df3_right, use_container_width=True)

                # Display notes, if any
                if len(summary.tables) > 3:
                    st.subheader("Примечания")
                    notes = summary.tables[3].data
                    st.text('\n'.join([row[0] for row in notes]))

                st.subheader("Пояснения к результатам модели")

                with st.expander("Как читать таблицу: Качество модели (R-squared и др.)"):
                    st.markdown("""
                    Эта таблица показывает, насколько хорошо ваша модель в целом описывает данные.

                    - **`R-squared` (R-квадрат)**: **Самый важный показатель здесь.** Он показывает, какой процент изменений цены ваша модель смогла объяснить. Значение `0.831` означает, что **83.1%** всех различий в ценах на автомобили объясняются факторами, которые вы включили в модель (пробег, возраст и рынок). **Это очень высокий и хороший результат.**

                    - **`No. Observations` (Кол-во наблюдений)**: Количество автомобилей, использованных для построения модели. Больше — лучше.

                    - **`Prob (F-statistic)` (Вероятность F-статистики)**: Отвечает на вопрос: "А имеет ли наша модель вообще смысл?". Если это значение очень маленькое (например, `0.00`), то ответ — **"да, однозначно имеет"**.

                    **Вывод:** Эти цифры дают вам уверенность в том, что выводам модели можно доверять.
                    """)

                with st.expander("Как читать таблицу: Влияние факторов (коэффициенты)"):
                    st.markdown("""
                    Это "сердце" анализа. Каждая строка — это один из факторов, влияющих на цену.

                    - **`coef` (Коэффициент)**: Показывает "силу" и "направление" влияния фактора на логарифм цены.
                        - **`age` (Возраст)**: Отрицательный коэффициент (например, `-0.06`) означает, что каждый дополнительный год **уменьшает** цену примерно на 6%.
                        - **`market_...`**: Положительный коэффициент (например, `0.105`) означает, что при одинаковом возрасте и пробеге, автомобиль на этом рынке в среднем **дороже** базового рынка примерно на 10.5%.

                    - **`P>|t|` (p-значение)**: **Ключевой столбец.** Показывает, является ли влияние фактора статистически значимым или это просто случайность.
                        - **Правило простое:** если p-значение **меньше 0.05**, то влияние реально и не случайно. У всех ваших факторов p-значение `0.000`, что подтверждает их сильное влияние.

                    **Практическое применение:**
                    1. Вы можете количественно оценить влияние: "Каждый год старения отнимает ~6% цены".
                    2. Вы доказали, что разница в ценах между рынками — это реальный эффект, а не случайность.
                    """)

                with st.expander("Как читать таблицу: Техническая диагностика"):
                    st.markdown("""
                    Эта часть больше для статистиков, но вот простое объяснение:

                    - **`Durbin-Watson`**: Тест на одну из технических характеристик модели. Значение около 2 (у вас ~1.8) считается хорошим.

                    - **`Cond. No.` (Число обусловленности)**: Проверяет, нет ли в модели "конфликтующих" факторов. Ваше значение велико, и модель выдает предупреждение.
                        - **Что это значит?** Это ожидаемо, так как `пробег` и `пробег в квадрате` сильно связаны. Для вашей аналитической задачи это **не является критической проблемой**.

                    **Вывод:** Диагностика в целом удовлетворительная, и на предупреждение о `Cond. No.` в данном случае можно не обращать пристального внимания.
                    """)

                with st.expander("Как читать график? (Тренды и коридоры)"):
                    st.markdown("""
                    График выше показывает зависимость цены от пробега с дополнительными аналитическими слоями.

                    - **Цветные точки**: Каждая точка — это отдельный автомобиль с одного из рынков (`mobile.de` или `polovni_automobili`).

                    - **Цветные линии (Тренды)**: Это "сглаженные" средние линии цен для каждого рынка. Они показывают общую тенденцию: как в среднем падает цена с увеличением пробега на каждой площадке.

                    - **Пунктирные линии (Ценовые коридоры)**: Они делят все автомобили на ценовые слои:
                        - **Коридор "25% / 75%" (внутренний)**: Здесь находится "ядро" рынка — 50% автомобилей со средними, самыми типичными ценами.
                        - **Коридор "10% / 90%" (внешний)**:
                            - Ниже нижней линии находятся **10% самых дешевых** автомобилей (зона выгодных сделок).
                            - Выше верхней линии находятся **10% самых дорогих** автомобилей.

                    **Как это использовать?**
                    Оцените, в какой коридор попадает интересующий вас автомобиль. Если он ниже линии 10%, это очень дешевое предложение. Если он внутри коридора 25-75%, его цена считается "нормальной".
                    """)
            else:
                st.warning("Недостаточно данных для построения гедонистической модели.")

        else:
            st.warning("Нет данных для выбранной модели для сравнения.")
    else:
        st.warning("Нет доступных моделей для сравнения. Примените фильтры или соберите данные.")

# --- Sidebar Export Button (MOVED TO THE END OF THE SCRIPT) ---
st.sidebar.divider()
st.sidebar.subheader("Экспорт")
if st.sidebar.button("Сохранить отчет в HTML"):
    if not filtered_df.empty:
        # --- Part 1: Scatter Plot ---
        graph_html = fig.to_html(include_plotlyjs='cdn')
        js_code = '<script>var plot_div = document.getElementsByClassName(\"plotly-graph-div\")[0]; plot_div.on(\"plotly_click\", function(data){if(data.points.length > 0){var point = data.points[0]; var url = point.customdata[0]; if(url){window.open(url, \"_blank\");}}});</script>'
        graph_html = graph_html.replace('</body>', js_code + '</body>')

        # --- Listings Summary for HTML ---
        if not filtered_df.empty:
            source_counts = filtered_df['source'].value_counts().to_dict()
            summary_parts_html = [f"<strong>{source}</strong>: {count}" for source, count in source_counts.items()]
            listings_summary_html = f'<p><strong>Количество объявлений по источникам:</strong> {", ".join(summary_parts_html)}</p>'
        else:
            listings_summary_html = ""

        # --- Part 2: Top Deals Table ---
        deals_for_html = top_deals_df.copy()
        deals_for_html.index = np.arange(1, len(deals_for_html) + 1)
        deals_for_html.index.name = "№"
        deals_for_html['url'] = deals_for_html['url'].apply(lambda x: f'<a href="{x}" target="_blank">Перейти</a>')
        table_html = deals_for_html.to_html(index=True, justify='left', border=0, classes='deals_table', escape=False, table_id="deals-table")

        # --- Part 3: Detailed Comparison (Robust version) ---
        comparison_html_parts = []
        if available_search_groups:
            model_comparison_df_report = filtered_df[filtered_df['search_group'] == selected_model_for_comparison].copy()
            
            if not model_comparison_df_report.empty:
                comparison_html_parts.append('<div class="report-section">')
                comparison_html_parts.append(f"<h2>📊 Детальное сравнение цен для {selected_model_for_comparison}</h2>")

                # Stats Table
                price_stats_report = calculate_price_statistics(model_comparison_df_report)
                if not price_stats_report.empty:
                    stats_table_html = price_stats_report.style.format({
                        'mean': "€{:,.0f}", 'median': "€{:,.0f}", 'std': "€{:,.0f}",
                        '25th_percentile': "€{:,.0f}", '75th_percentile': "€{:,.0f}"
                    }).to_html(index=True, justify='left', border=0, classes='deals_table', table_uuid='stats-table')
                    comparison_html_parts.append("<h3>Статистика цен</h3>")
                    comparison_html_parts.append(stats_table_html)
                else:
                    comparison_html_parts.append("<p>Нет данных для отображения статистики по выбранной модели.</p>")

                # Median Difference Text
                if len(price_stats_report) > 1:
                    medians = price_stats_report['median'].to_dict()
                    sources = list(medians.keys())
                    if len(sources) == 2:
                        source1, source2 = sources[0], sources[1]
                        median1, median2 = medians[source1], medians[source2]
                        if median1 > 0 and median2 > 0:
                            percentage_diff = ((median2 - median1) / median1) * 100
                            diff_text = f"<strong>Разница медианных цен ({source2} относительно {source1}):</strong> {percentage_diff:,.2f}%"
                            if percentage_diff > 0:
                                diff_text += f'<br><span style="color: #ff7675;">На сайте {source2} медианная цена выше на {percentage_diff:,.2f}%.</span>'
                            else:
                                diff_text += f'<br><span style="color: #55efc4;">На сайте {source2} медианная цена ниже на {abs(percentage_diff):,.2f}%.</span>'
                            comparison_html_parts.append(f'<p style="font-size: 1.1rem;">{diff_text}</p>')
                comparison_html_parts.append('</div>')

                # Box Plot
                comparison_html_parts.append('<div class="report-section">')
                fig_box_report = create_price_distribution_box_plot(model_comparison_df_report)
                box_plot_html = fig_box_report.to_html(include_plotlyjs=False)
                comparison_html_parts.append("<h3>Распределение цен по источникам</h3>")
                comparison_html_parts.append(box_plot_html)
                comparison_html_parts.append('</div>')

                # Econometrics Plot
                comparison_html_parts.append('<div class="report-section">')
                comparison_html_parts.append("<h2>🔬 Эконометрический анализ</h2>")
                econometrics_fig_report = create_quantile_lowess_plot(model_comparison_df_report)
                econometrics_plot_html = econometrics_fig_report.to_html(include_plotlyjs=False)
                comparison_html_parts.append(econometrics_plot_html)

                # Hedonic Model Results for HTML
                hedonic_model_report = run_hedonic_model(model_comparison_df_report)
                if hedonic_model_report:
                    comparison_html_parts.append("<h3>Результаты гедонистической модели</h3>")
                    market_coeffs_report = {k: v for k, v in hedonic_model_report.params.items() if 'C(market' in k}
                    if market_coeffs_report:
                        for market, coeff in market_coeffs_report.items():
                            market_name = market.split('.')[-1].split(']')[0]
                            premium = (np.exp(coeff) - 1) * 100
                            comparison_html_parts.append(f"<p><strong>Премия рынка {market_name}:</strong> {premium:.2f}%</p>")
                    
                    comparison_html_parts.append("<h4>Полная таблица с коэффициентами:</h4>")
                    comparison_html_parts.append(f"<pre>{hedonic_model_report.summary()}</pre>")

                comparison_html_parts.append('</div>')

        final_comparison_html = "\n".join(comparison_html_parts)

        # --- Assemble Final HTML ---
        title_str = f"📊 Сравнительный анализ рынков автомобилей: {', '.join(sorted(filtered_df['comparison_group'].unique()))}"
        
        css_style = """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; background-color: #111; color: #eee; margin: 2rem; }
            h1, h2, h3 { color: #eee; border-bottom: 1px solid #444; padding-bottom: 10px; font-weight: 400; }
            h1 { font-size: 2.2rem; }
            h2 { font-size: 1.75rem; margin-top: 3rem; }
            h3 { font-size: 1.4rem; margin-top: 2rem; border-bottom: none; }
            .report-section { margin-bottom: 2rem; padding: 1rem; background-color: #1e1e1e; border-radius: 8px; }
            .deals_table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
            .deals_table th, .deals_table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }
            .deals_table th { background-color: #222; cursor: pointer; }
            .deals_table tr:hover { background-color: #2a2a2a; }
            .deals_table th.sort-up::after { content: \" ▲\"; }
            .deals_table th.sort-down::after { content: \" ▼\"; }
            a { color: #3498db; text-decoration: none; }
            a:hover { text-decoration: underline; }
            p { margin: 1rem 0; line-height: 1.6; }
            #T_stats-table { width: 100%; }
            #T_stats-table th, #T_stats-table td { text-align: center; }
        </style>
        """

        report_html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Аналитический отчет</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/vanilla-js-tablesort@0.1.0/dist/vanilla-js-tablesort.min.js"></script>
                {css_style}
            </head>
            <body>
                <h1>{title_str}</h1>
                <div class="report-section">{graph_html}</div>
                {listings_summary_html}
                <div class="report-section">
                    <h2>Топ-2 самых дешевых предложения по группам пробега</h2>
                    {table_html}
                </div>
                {final_comparison_html}
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