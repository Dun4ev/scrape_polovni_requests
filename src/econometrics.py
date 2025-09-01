import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import statsmodels.api as sm
import pandas as pd
from datetime import datetime
import statsmodels.formula.api as smf

def create_quantile_lowess_plot(df):
    """
    Creates a scatter plot with quantile corridors and a LOWESS trend line for each market.
    """
    fig = go.Figure()

    if df.empty or df['price_eur'].isnull().all() or df['mileage_km'].isnull().all():
        return fig

    # Define a color map for markets
    markets = sorted(df['source'].unique())
    colors = px.colors.qualitative.Plotly
    color_map = {market: colors[i % len(colors)] for i, market in enumerate(markets)}

    # Quantile corridors (calculated on the whole dataset)
    quantiles = [0.1, 0.25, 0.75, 0.9]
    quantile_labels = {0.1: "10% / 90%", 0.9: "10% / 90%", 0.25: "25% / 75%", 0.75: "25% / 75%"}
    added_quantile_legends = set()

    for q in quantiles:
        price_quantile = df['price_eur'].quantile(q)
        fig.add_shape(
            type="line",
            x0=df['mileage_km'].min(),
            y0=price_quantile,
            x1=df['mileage_km'].max(),
            y1=price_quantile,
            line=dict(color="rgba(255, 255, 255, 0.2)", width=1, dash="dash"),
        )
        # Add a dummy trace for the legend, only once per pair
        label = quantile_labels[q]
        if label not in added_quantile_legends:
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='lines',
                line=dict(color="rgba(255, 255, 255, 0.4)", width=1, dash="dash"),
                name=label
            ))
            added_quantile_legends.add(label)

    # Plot LOWESS and scatter for each market
    for market in markets:
        market_df = df[df['source'] == market]
        if market_df.empty or market_df.shape[0] < 2: # Need at least 2 points for a line
            continue

        # LOWESS trend
        try:
            lowess = sm.nonparametric.lowess
            trend = lowess(market_df['price_eur'], market_df['mileage_km'], frac=0.5)
        except Exception:
            continue # Skip if LOWESS fails for any reason

        fig.add_trace(go.Scatter(
            x=trend[:, 0],
            y=trend[:, 1],
            mode='lines',
            name=f'Тренд {market}',
            line=dict(color=color_map[market], width=4) # Made line thicker
        ))

        # Scatter plot of the actual data
        fig.add_trace(go.Scatter(
            x=market_df['mileage_km'],
            y=market_df['price_eur'],
            mode='markers',
            name=market,
            marker=dict(color=color_map[market], opacity=0.4, size=5), # Made markers smaller
            text=market_df['title'],
            hovertemplate="<b>%{text}</b><br><b>Источник:</b> "+ market +"<br><b>Цена:</b> %{y:,.0f} €<br><b>Пробег:</b> %{x:,.0f} km<extra></extra>"
        ))

    fig.update_layout(
        title="Сравнение трендов цен по рынкам",
        xaxis_title="Пробег, км",
        yaxis_title="Цена, €",
        template="plotly_dark",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )

    return fig

def run_hedonic_model(df):
    """
    Runs a hedonic regression model to estimate the market premium.
    """
    if df.empty or df.shape[0] < 10:  # Need enough data to run regression
        return None

    df_model = df.copy()
    df_model['log_price'] = np.log(df_model['price_eur'])
    df_model['age'] = datetime.now().year - df_model['year']
    df_model['market'] = pd.Categorical(df_model['source'])

    # Ensure there are at least two markets to compare
    if len(df_model['market'].cat.categories) < 2:
        return None

    # Create dummy variables manually for more control over names
    reference_market = df_model['market'].cat.categories[0]
    dummy_names = []
    for market_name in df_model['market'].cat.categories[1:]:
        # Create a clean name for the variable, e.g., "market_polovni_automobili"
        clean_name = f"market_{market_name}"
        df_model[clean_name] = (df_model['market'] == market_name).astype(int)
        dummy_names.append(clean_name)

    # Build the formula string with the new dummy variables
    if not dummy_names:
        return None # No markets to compare
        
    dummy_vars_str = ' + '.join(dummy_names)
    formula = f'log_price ~ mileage_km + I(mileage_km**2) + age + {dummy_vars_str}'
    
    try:
        model = smf.ols(formula, data=df_model).fit()
        # Store reference market in the model for later use
        model.reference_market = reference_market
    except Exception as e:
        # Not enough data for all variables, etc.
        print(f"Could not fit hedonic model: {e}")
        return None

    return model