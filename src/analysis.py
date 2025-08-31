
import pandas as pd

def get_top_deals(df):
    if df.empty:
        return pd.DataFrame()
    max_km_limit = int(df['mileage_km'].max() + 50000)
    bins = list(range(0, max_km_limit, 50000))
    if not bins:
        return pd.DataFrame()
    labels = [f'{i/1000:,.0f} - {(i+50000)/1000:,.0f} тыс. км' for i in bins[:-1]]
    df['mileage_bin'] = pd.cut(df['mileage_km'], bins=bins, labels=labels, right=False)
    
    # Group by the new comparison group
    top_deals = df.groupby(['mileage_bin', 'comparison_group'], observed=False).apply(
        lambda x: x.nsmallest(2, 'price_eur')
    ).reset_index(drop=True)
    return top_deals

def calculate_price_statistics(df):
    """Calculates price statistics for a given dataframe."""
    if df.empty:
        return None

    price_stats = df.groupby('source')['price_eur'].agg(
        ['mean', 'median', 'std', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]
    ).rename(columns={'<lambda_0>': '25th_percentile', '<lambda_1>': '75th_percentile'})
    
    return price_stats
