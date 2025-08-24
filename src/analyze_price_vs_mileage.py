# analyze_price_vs_mileage.py
import pandas as pd, numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re

df = pd.read_csv("data/raw/polovni_automobili.csv")
df = df.dropna(subset=["price_eur","mileage_km","year"]).copy()

# Модель: цена ~ пробег(тыс.км) + год
X = np.c_[np.ones(len(df)), df["mileage_km"]/1000.0, df["year"]]
y = df["price_eur"].values
beta = np.linalg.pinv(X.T @ X) @ (X.T @ y)
df["pred_price_eur"] = (X @ beta)

resid = df["price_eur"] - df["pred_price_eur"]
mad = np.median(np.abs(resid - np.median(resid))) + 1e-9
z = (resid - np.median(resid)) / (1.4826 * mad)
df["zscore"] = z
df["is_outlier"] = np.abs(z) > 3

# Интерактивная визуализация (scatter)
fig = px.scatter(df, x="mileage_km", y="price_eur",
                 color="is_outlier",
                 hover_data=['title', 'year', 'price_eur', 'url'],
                 title="Volvo XC60 (>=2020): цена vs пробег")

# Линия тренда
mid_year = int(df["year"].median())
km_grid = np.linspace(df["mileage_km"].min(), df["mileage_km"].max(), 200)
trend = beta[0] + beta[1]*(km_grid/1000.0) + beta[2]*mid_year
fig.add_trace(go.Scatter(x=km_grid, y=trend, mode='lines', name=f'trend @ year={mid_year}'))

fig.update_layout(xaxis_title="Пробег, км", yaxis_title="Цена, €", clickmode='event+select')

# Обновляем всплывающую подсказку (без ссылки)
fig.update_traces(customdata=df[['url', 'year', 'title']],
                  hovertemplate="<b>%{customdata[2]}</b><br><br>" +
                                "<b>Цена:</b> %{y} €<br>" +
                                "<b>Пробег:</b> %{x} km<br>"+
                                "<b>Год:</b> %{customdata[1]}<br>"+
                                "<extra></extra>",
                  )

# Генерируем HTML для графика и добавляем JavaScript для кликабельности
html = fig.to_html(include_plotlyjs='cdn')

js_code = """
<script>
    var plot_div = document.getElementsByClassName('plotly-graph-div')[0];
    plot_div.on('plotly_click', function(data){
        if(data.points.length > 0) {
            var point = data.points[0];
            var url = point.customdata[0];
            window.open(url, '_blank');
        }
    });
</script>
"""

# Вставляем JavaScript в конец body
full_html = html.replace('</body>', js_code + '</body>')

with open("results/xc60_price_vs_mileage.html", "w", encoding="utf-8") as f:
    f.write(full_html)

# Кандидаты «выгодных» (ниже тренда на >1.5*MAD и не крайний outlier)
cheap = df[(z < -1.5) & (~df["is_outlier"])].sort_values("zscore")
cheap[["title","year","mileage_km","price_eur","pred_price_eur","zscore","url"]].to_csv(
    "results/xc60_candidates.csv", index=False)

print("Готово: интерактивный график results/xc60_price_vs_mileage.html, кандидаты results/xc60_candidates.csv")