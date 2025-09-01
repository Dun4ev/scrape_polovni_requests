import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import streamlit as st

def create_price_mileage_scatter_plot(df):
    """Creates a scatter plot of price vs. mileage."""
    fig = go.Figure()
    if not df.empty:
        unique_comparison_groups = sorted(df['comparison_group'].unique())
        color_map = {group: color for group, color in zip(unique_comparison_groups, px.colors.qualitative.Plotly)}
        
        for name, group_df in df.groupby('comparison_group'):
            if len(group_df) < 3: continue
            group_color = color_map.get(name, 'grey')
            
            custom_data = np.stack((group_df['url'], group_df['source']), axis=-1)

            fig.add_trace(go.Scatter(
                x=group_df['mileage_km'], y=group_df['price_eur'], mode='markers', name=name,
                marker=dict(color=group_color), 
                customdata=custom_data,
                text=group_df['title'],
                hovertemplate="<span style='font-size: 12px;'><b>%{text}</b><br>Цена: %{y:,.0f} €<br>Пробег: %{x:,.0f} km<br><b>Источник: %{customdata[1]}</b><br><i>Кликните для перехода</i></span><extra></extra>"
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

    fig.update_layout(xaxis_title="Пробег, км", yaxis_title="Цена, €", legend_title="Группы для сравнения", template="plotly_dark", height=650, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    return fig

def create_price_distribution_box_plot(df):
    """Creates a box plot of price distribution by source."""
    fig_box = px.box(df, x="source", y="price_eur", color="source",
                     title=f"Распределение цен для {df['search_group'].iloc[0]} по источникам",
                     labels={"price_eur": "Цена, €", "source": "Источник"},
                     template="plotly_dark")
    fig_box.update_layout(showlegend=False) # Hide legend as source is on x-axis
    return fig_box