import pandas as pd
import requests
import io
import json
from datetime import datetime

def fetch_nse_data(ticker):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.NS?range=2y&interval=1d"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return pd.DataFrame()
        data = res.json()
        timestamps = data['chart']['result'][0]['timestamp']
        indicators = data['chart']['result'][0]['indicators']['quote'][0]
        return pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close']
        }, index=pd.to_datetime(timestamps, unit='s')).dropna()
    except Exception:
        return pd.DataFrame()

def detect_zones(df, tf_code):
    if df.empty or len(df) < 10:
        return []
    
    buffer_limits = {'D': 0.03, 'W': 0.08, 'M': 0.12, 'Q': 0.12, 'HY': 0.12, 'Y': 0.12}
    buffer_pct = buffer_limits.get(tf_code, 0.03)
    results = []

    high, low, close, open_p = df['High'].astype(float), df['Low'].astype(float), df['Close'].astype(float), df['Open'].astype(float)
    total_range = high - low
    body_range = (close - open_p).abs()
    cmp = float(close.iloc[-1])

    for i in range(len(df) - 12, len(df) - 1):
        if i < 1:
            continue
        
        base_indices = []
        for b in range(1, 5):
            idx = i - b
            if idx >= 0 and body_range.iloc[idx] <= (0.50 * total_range.iloc[idx]):
                base_indices.append(idx)
            else:
                break

        if 1 <= len(base_indices) <= 4:
            first_base_idx = base_indices[-1]
            legin_idx = first_base_idx - 1
            base_df = df.iloc[base_indices]
            subsequent_df = df.iloc[i + 1 : -1]

            # DEMAND ZONE
            gap_legout_dz = max(0.0, float(open_p.iloc[i] - close.iloc[i - 1]))
            effective_legout_dz = body_range.iloc[i] + gap_legout_dz
            if close.iloc[i] > open_p.iloc[i] and effective_legout_dz > (0.50 * total_range.iloc[i]):
                legin_body = body_range.iloc[legin_idx] if legin_idx >= 0 else 0
                legin_close = close.iloc[legin_idx] if legin_idx >= 0 else 0
                gap_legin = max(0.0, float(open_p.iloc[first_base_idx] - legin_close))
                effective_legin = max(legin_body, gap_legin)

                if effective_legout_dz > effective_legin:
                    proximal = float(max(base_df['Open'].max(), base_df['Close'].max()))
                    distal = float(base_df['Low'].min())
                    if proximal < cmp <= (proximal * (1 + buffer_pct)):
                        if subsequent_df.empty or not (subsequent_df['Low'] <= proximal).any():
                            results.append({
                                'Timeframe': tf_code,
                                'Zone_Type': 'DZ',
                                'Classification': f"{tf_code}DZ",
                                'CMP': round(cmp, 2),
                                'Proximal': round(proximal, 2),
                                'Distal': round(distal, 2)
                            })

            # SUPPLY ZONE
            gap_legout_sz = max(0.0, float(close.iloc[i - 1] - open_p.iloc[i]))
            effective_legout_sz = body_range.iloc[i] + gap_legout_sz
            if close.iloc[i] < open_p.iloc[i] and effective_legout_sz > (0.50 * total_range.iloc[i]):
                legin_body = body_range.iloc[legin_idx] if legin_idx >= 0 else 0
                legin_close = close.iloc[legin_idx] if legin_idx >= 0 else float('inf')
                gap_legin = max(0.0, float(legin_close - open_p.iloc[first_base_idx])) if legin_idx >= 0 else 0
                effective_legin = max(legin_body, gap_legin)

                if effective_legout_sz > effective_legin:
                    proximal = float(min(base_df['Open'].min(), base_df['Close'].min()))
                    distal = float(base_df['High'].max())
                    if (proximal * (1 - buffer_pct)) <= cmp < proximal:
                        if subsequent_df.empty or not (subsequent_df['High'] >= proximal).any():
                            results.append({
                                'Timeframe': tf_code,
                                'Zone_Type': 'SZ',
                                'Classification': f"{tf_code}SZ",
                                'CMP': round(cmp, 2),
                                'Proximal': round(proximal, 2),
                                'Distal': round(distal, 2)
                            })
    return results

def run_daily_analysis():
    url = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    symbols = pd.read_csv(io.StringIO(res.text))['Symbol'].tolist() if res.status_code == 200 else ["RELIANCE", "TCS", "INFY"]

    all_matches = []
    
    for symbol in symbols:
        raw_df = fetch_nse_data(symbol)
        if raw_df.empty:
            continue
        
        tf_map = {
            'D': raw_df,
            'W': raw_df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            'M': raw_df.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            'Q': raw_df.resample('QE').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            'HY': raw_df.resample('6ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna(),
            'Y': raw_df.resample('YE').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
        }

        for tf_code, tf_df in tf_map.items():
            zones = detect_zones(tf_df, tf_code)
            for z in zones:
                z['Symbol'] = symbol
                all_matches.append(z)

    output_data = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S IST'),
        'results': all_matches
    }
    with open('scan_results.json', 'w') as f:
        json.dump(output_data, f, indent=2)

if __name__ == "__main__":
    run_daily_analysis()