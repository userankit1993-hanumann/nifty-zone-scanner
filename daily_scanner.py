import pandas as pd
import yfinance as yf
import json

# Full Nifty 500 Ticker List
NIFTY_500_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS",
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS",
    "HCLTECH.NS", "ADANIENT.NS", "ASIANPAINT.NS", "TITAN.NS", "ULTRACEMCO.NS", "SUNPHARMA.NS",
    "BAJFINANCE.NS", "DMART.NS", "NESTLEIND.NS", "WIPRO.NS", "M&M.NS", "NTPC.NS", "TATAMOTORS.NS",
    "POWERGRID.NS", "ONGC.NS", "JSWSTEEL.NS", "ADANIPORTS.NS", "COALINDIA.NS", "TATASTEEL.NS",
    "BAJAJFINSV.NS", "PIDILITIND.NS", "IOC.NS", "GRASIM.NS", "SIEMENS.NS", "BEL.NS", "SBILIFE.NS",
    "VBL.NS", "DLF.NS", "HAL.NS", "BPCL.NS", "INDIGO.NS", "ABB.NS", "HDFCLIFE.NS", "TATACONSUM.NS",
    "GAIL.NS", "BANKBARODA.NS", "EICHERMOT.NS", "DIVISLAB.NS", "CHOLAFIN.NS", "DRREDDY.NS",
    "HAVELLS.NS", "BAJAJ-AUTO.NS", "AMBUJACEM.NS", "CIPLA.NS", "HEROMOTOCO.NS", "SRF.NS",
    "VEDL.NS", "SHREECEM.NS", "MARUTI.NS", "TECHM.NS", "APOLLOHOSP.NS", "BRITANNIA.NS",
    "TRENT.NS", "GODREJCP.NS", "PFC.NS", "REC.NS", "TATAELXSI.NS", "CANBK.NS", "PNB.NS",
    "IDFCFIRSTB.NS", "MOTHERSON.NS", "POLYCAB.NS", "ASHOKLEY.NS", "JIOFIN.NS", "ZYDUSLIFE.NS",
    "BSE.NS", "MCX.NS", "TATAPOWER.NS", "NHPC.NS", "IRFC.NS", "RVNL.NS", "MAZDOCK.NS"
]

# Exact Proximity Thresholds
TIMEFRAME_THRESHOLDS = {
    'Daily': 0.03,        # Within 3% of Demand Zone Low
    'Weekly': 0.10,       # Within 10%
    'Monthly': 0.12,      # Within 12%
    'Quarterly': 0.12,    # Within 12%
    'Half-Yearly': 0.12,  # Within 12%
    'Yearly': 0.12        # Within 12%
}

def analyze_zone_and_gap(df, timeframe):
    """Calculates DZ proximity and gap formation relative to 3:35 PM IST close"""
    if df is None or len(df) < 2:
        return None
    
    last_close = float(df['Close'].iloc[-1])
    last_open = float(df['Open'].iloc[-1])
    prev_high = float(df['High'].iloc[-2]) if len(df) >= 2 else float(df['High'].iloc[-1])
    
    lookback = min(len(df), 10)
    demand_base = float(df['Low'].tail(lookback).min())
    
    pct_threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
    max_dz_price = demand_base * (1 + pct_threshold)
    
    if demand_base <= last_close <= max_dz_price:
        has_gap = last_open > prev_high
        dist_from_dz = round(((last_close - demand_base) / demand_base) * 100, 2)
        return {
            "in_dz": True,
            "has_gap": has_gap,
            "distance_pct": dist_from_dz
        }
    return None

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

def scan_stocks():
    print("Running 3:35 PM IST Demand Zone and Gap Scan...")
    results = {
        "Daily": {"DZ": []},
        "Weekly": {"DZ": []},
        "Monthly": {"DZ": []},
        "Quarterly": {"DZ": []},
        "Half-Yearly": {"DZ": []},
        "Yearly": {"DZ": []}
    }
    
    timeframes = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']

    for symbol in NIFTY_500_SYMBOLS:
        try:
            stock_name = symbol.replace('.NS', '')
            df_daily = yf.download(symbol, period="5y", interval="1d", progress=False)
            
            if df_daily.empty:
                continue
                
            if isinstance(df_daily.columns, pd.MultiIndex):
                df_daily.columns = df_daily.columns.get_level_values(0)

            df_daily = df_daily.dropna()

            for tf in timeframes:
                df_tf = resample_data(df_daily, tf)
                zone_info = analyze_zone_and_gap(df_tf, tf)
                
                if zone_info and zone_info["in_dz"]:
                    results[tf]["DZ"].append({
                        "symbol": stock_name,
                        "dist_pct": zone_info["distance_pct"],
                        "has_gap": zone_info["has_gap"]
                    })
        except Exception:
            continue

    with open('scan_results.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print("3:35 PM Scan complete. Results saved to scan_results.json.")

if __name__ == "__main__":
    scan_stocks()
