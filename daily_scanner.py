import pandas as pd
import yfinance as yf
import json
import requests
import io

def get_nifty500_symbols():
    """Fetch official Nifty 500 symbols dynamically from NSE"""
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        symbols = [f"{symbol.strip()}.NS" for symbol in df['Symbol'].dropna()]
        return symbols
    except Exception as e:
        print(f"Error fetching Nifty 500 list: {e}")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS"]

def calculate_zones(df):
    """Classify into Demand Zone (DZ) or Supply Zone (SZ)"""
    if len(df) < 5:
        return "Neutral"
    
    latest_close = df['Close'].iloc[-1]
    low_min = df['Low'].tail(5).min()
    high_max = df['High'].tail(5).max()
    
    if high_max == low_min:
        return "Neutral"
        
    dz_threshold = low_min + (high_max - low_min) * 0.15
    sz_threshold = high_max - (high_max - low_min) * 0.15
    
    if latest_close <= dz_threshold:
        return "Demand Zone (DZ)"
    elif latest_close >= sz_threshold:
        return "Supply Zone (SZ)"
    return "Neutral"

def resample_data(df, timeframe):
    """Resample daily OHLC data into multiple timeframes using universal rules"""
    rule_map = {
        'Daily': 'D',
        'Weekly': 'W',
        'Monthly': 'ME',
        'Quarterly': '3ME',
        'Half-Yearly': '6ME',
        'Yearly': 'YE'
    }
    rule = rule_map.get(timeframe, 'D')
    try:
        resampled = df.resample(rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()
        return resampled
    except Exception:
        # Fallback for older pandas versions
        old_rule_map = {'Monthly': 'M', 'Quarterly': '3M', 'Half-Yearly': '6M', 'Yearly': 'Y'}
        resampled = df.resample(old_rule_map.get(timeframe, rule)).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()
        return resampled

def scan_nifty_500():
    symbols = get_nifty500_symbols()
    print(f"Scanning {len(symbols)} Nifty 500 stocks...")
    
    results = {
        "Daily": {"DZ": [], "SZ": []},
        "Weekly": {"DZ": [], "SZ": []},
        "Monthly": {"DZ": [], "SZ": []},
        "Quarterly": {"DZ": [], "SZ": []},
        "Half-Yearly": {"DZ": [], "SZ": []},
        "Yearly": {"DZ": [], "SZ": []}
    }
    
    # Download data
    try:
        data = yf.download(symbols, period="2y", interval="1d", group_by="ticker", threads=True, progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    timeframes = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']

    for symbol in symbols:
        try:
            stock_name = symbol.replace('.NS', '')
            
            # Retrieve single ticker DataFrame safely
            if len(symbols) == 1:
                df_daily = data.dropna()
            else:
                if symbol in data and not data[symbol].dropna().empty:
                    df_daily = data[symbol].dropna()
                else:
                    continue

            for tf in timeframes:
                df_tf = resample_data(df_daily, tf)
                zone = calculate_zones(df_tf)
                
                if zone == "Demand Zone (DZ)":
                    results[tf]["DZ"].append(stock_name)
                elif zone == "Supply Zone (SZ)":
                    results[tf]["SZ"].append(stock_name)
        except Exception as e:
            continue

    with open('scan_results.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print("Nifty 500 scan complete. JSON saved successfully.")

if __name__ == "__main__":
    scan_nifty_500()
    
