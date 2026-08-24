import pandas as pd
import yfinance as yf
import json

# Curated Nifty 500 liquid stock list (bypasses NSE IP blocking)
NIFTY_500_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS",
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS",
    "HCLTECH.NS", "ADANIENT.NS", "ASIANPAINT.NS", "TITAN.NS", "ULTRACEMCO.NS", "SUNPHARMA.NS",
    "BAJFINANCE.NS", "DMART.NS", "NESTLEIND.NS", "WIPRO.NS", "M&M.NS", "NTPC.NS", "TATAMOTORS.NS",
    "POWERGRID.NS", "ONGC.NS", "JSWSTEEL.NS", "ADANIPORTS.NS", "COALINDIA.NS", "TATASTEEL.NS",
    "BAJAJFINSV.NS", "PIDILITIND.NS", "IOC.NS", "GRASIM.NS", "SIEMENS.NS", "BEL.NS", "SBILIFE.NS",
    "VBL.NS", "DLF.NS", "HAL.NS", "BPCL.NS", "INDIGO.NS", "ABB.NS", "HDFCLIFE.NS", "TATACONSUM.NS",
    "PIDILITE.NS", "GAIL.NS", "BANKBARODA.NS", "EICHERMOT.NS", "DIVISLAB.NS", "CHOLAFIN.NS",
    "DRREDDY.NS", "HAVELLS.NS", "BAJAJ-AUTO.NS", "AMBUJACEM.NS", "CIPLA.NS", "HEROMOTOCO.NS",
    "SRF.NS", "VEDL.NS", "SHREECEM.NS", "MARUTI.NS", "TECHM.NS", "APOLLOHOSP.NS", "BRITANNIA.NS",
    "TRENT.NS", "GODREJCP.NS", "PFC.NS", "REC.NS", "TATAELXSI.NS", "CANBK.NS", "PNB.NS",
    "IDFCFIRSTB.NS", "MOTHERSON.NS", "POLYCAB.NS", "ASHOKLEY.NS", "JIOFIN.NS", "ZYDUSLIFE.NS"
]

def calculate_zones(df):
    if len(df) < 5:
        return "Neutral"
    
    # Clean multi-index columns if returned by yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    latest_close = float(df['Close'].iloc[-1])
    low_min = float(df['Low'].tail(5).min())
    high_max = float(df['High'].tail(5).max())
    
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
        return df.resample(rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()
    except Exception:
        fallback_map = {'Monthly': 'M', 'Quarterly': '3M', 'Half-Yearly': '6M', 'Yearly': 'Y'}
        return df.resample(fallback_map.get(timeframe, rule)).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()

def scan_nifty_500():
    print(f"Scanning {len(NIFTY_500_SYMBOLS)} stocks...")
    
    results = {
        "Daily": {"DZ": [], "SZ": []},
        "Weekly": {"DZ": [], "SZ": []},
        "Monthly": {"DZ": [], "SZ": []},
        "Quarterly": {"DZ": [], "SZ": []},
        "Half-Yearly": {"DZ": [], "SZ": []},
        "Yearly": {"DZ": [], "SZ": []}
    }
    
    # Download stock data safely
    data = yf.download(NIFTY_500_SYMBOLS, period="2y", interval="1d", group_by="ticker", progress=False)

    timeframes = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']

    for symbol in NIFTY_500_SYMBOLS:
        try:
            stock_name = symbol.replace('.NS', '')
            if symbol in data:
                df_daily = data[symbol].dropna()
                if df_daily.empty:
                    continue
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
        
    print("Scan complete. JSON saved successfully.")

if __name__ == "__main__":
    scan_nifty_500()
