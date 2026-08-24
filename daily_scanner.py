import io
import json
import pandas as pd
import requests
import yfinance as yf

# Entry threshold tolerance relative to CMP (e.g., within 3% on Daily, 10% on Weekly)
TIMEFRAME_THRESHOLDS = {
    'Daily': 0.05,
    'Weekly': 0.10,
    'Monthly': 0.15,
    'Quarterly': 0.15,
    'Half-Yearly': 0.15,
    'Yearly': 0.15,
}


def get_nifty_500_symbols():
  """Fetches live Nifty 500 list from official NSE indices source with fallback."""
  url = 'https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv'
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      )
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
      df = pd.read_csv(io.StringIO(response.text))
      if 'Symbol' in df.columns:
        return [f'{sym.strip()}.NS' for sym in df['Symbol'].dropna()]
  except Exception:
    pass

  # Fallback to standard top Nifty symbols if network fails
  return [
      'RELIANCE.NS',
      'TCS.NS',
      'HDFCBANK.NS',
      'INFY.NS',
      'ICICIBANK.NS',
      'HINDUNILVR.NS',
      'ITC.NS',
      'SBIN.NS',
      'BHARTIARTL.NS',
      'LTIM.NS',
  ]


def is_exciting_candle(row, prev_row=None):
  """GTF Exciting Candle check: Body > 50% of Range.

  Includes GTF Gap Treatment: If a Gap-Up occurred, the total range is
  measured from previous High to current High.
  """
  c_open = float(row['Open'])
  c_high = float(row['High'])
  c_low = float(row['Low'])
  c_close = float(row['Close'])
  body = abs(c_close - c_open)

  # Gap-Up Treatment: Gap extending range to current body
  if prev_row is not None and c_open > float(prev_row['High']):
    gap_range = c_high - float(prev_row['High'])
    if gap_range > 0 and (body / gap_range) >= 0.50:
      return True, True

  candle_range = c_high - c_low
  if candle_range == 0:
    return False, False

  return (body / candle_range) > 0.50, False


def resample_data(df, timeframe):
  """Resamples daily OHLC data cleanly into higher timeframes."""
  rule_map = {
      'Daily': 'D',
      'Weekly': 'W',
      'Monthly': 'ME',
      'Quarterly': '3ME',
      'Half-Yearly': '6ME',
      'Yearly': 'YE',
  }
  rule = rule_map.get(timeframe, 'D')
  if rule == 'D':
    return df

  try:
    resampled = (
        df.resample(rule)
        .agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        .dropna()
    )
    return resampled
  except Exception:
    fallback_map = {
        'Monthly': 'M',
        'Quarterly': '3M',
        'Half-Yearly': '6M',
        'Yearly': 'Y',
    }
    return (
        df.resample(fallback_map.get(timeframe, rule))
        .agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        .dropna()
    )


def is_demand_zone_fresh(df, legout_idx, proximal):
  """BACKTESTED FRESHNESS CHECK: Iterates forward from Leg-Out to latest bar.

  If ANY candle's Low dropped to or below the Proximal line, the zone is TESTED.
  """
  subsequent_candles = df.iloc[legout_idx + 1 :]
  if subsequent_candles.empty:
    return True

  # Check if price ever penetrated proximal line
  min_subsequent_low = float(subsequent_candles['Low'].min())
  return min_subsequent_low > proximal


def find_fresh_demand_zones(df, timeframe):
  """ACCURATE GTF DEMAND ZONE SCANNER (FRESH ONLY):

  - Leg-Out MUST be GREEN (Close > Open) and Exciting (>50% body)
  - Base Candles: 1 to 4 MAX (Body <= 50%)
  - Leg-In MUST be Exciting (>50% body)
  - Proximal Line: MAX of Open/Close bodies strictly across base candles
  - Distal Line: MIN Low across base candles & leg-out/leg-in wicks
  """
  if len(df) < 10:
    return []

  cmp = float(df['Close'].iloc[-1])
  threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
  dz_results = []

  # Search backward from recent bars to find the LATEST demand zone
  for i in range(len(df) - 2, max(len(df) - 80, 5), -1):
    legout_row = df.iloc[i]
    prev_row = df.iloc[i - 1]

    # Leg-Out MUST be GREEN (Bullish) for Demand Zone
    if float(legout_row['Close']) <= float(legout_row['Open']):
      continue

    is_legout_ex, has_gap_out = is_exciting_candle(legout_row, prev_row)
    if not is_legout_ex:
      continue

    # Identify Base Candles (Strictly 1 to 4 Base Candles)
    base_indices = []
    b_idx = i - 1
    while b_idx >= 0:
      row = df.iloc[b_idx]
      p_row = df.iloc[b_idx - 1] if b_idx > 0 else None
      is_ex, _ = is_exciting_candle(row, p_row)

      if not is_ex:
        base_indices.append(b_idx)
        b_idx -= 1
        if len(base_indices) > 4:  # Hard limit: Max 4 Base Candles
          break
      else:
        break

    num_bases = len(base_indices)
    if num_bases < 1 or num_bases > 4:  # GTF Rule: 1 to 4 bases only
      continue

    # Identify Leg-In Candle
    legin_idx = base_indices[-1] - 1
    if legin_idx < 0:
      continue

    legin_row = df.iloc[legin_idx]
    p_legin = df.iloc[legin_idx - 1] if legin_idx > 0 else None
    is_legin_ex, _ = is_exciting_candle(legin_row, p_legin)
    if not is_legin_ex:
      continue

    base_df = df.iloc[base_indices[::-1]]
    pattern = (
        'RBR'
        if float(legin_row['Close']) > float(legin_row['Open'])
        else 'DBR'
    )

    # --- ACCURATE GTF MARKINGS ---
    # 1. Proximal Line: Highest body border among base candles
    base_bodies = base_df[['Open', 'Close']].values.flatten()
    proximal = float(max(base_bodies))

    # 2. Distal Line: Lowest low among base candles, leg-out, and leg-in wicks
    distal = float(base_df['Low'].min())
    if float(legout_row['Low']) < distal:
      distal = float(legout_row['Low'])
    if float(legin_row['Low']) < distal:
      distal = float(legin_row['Low'])

    # Validate zone structure
    if proximal <= distal:
      continue

    # 3. BACKTESTED FRESHNESS CHECK
    if not is_demand_zone_fresh(df, i, proximal):
      continue  # Zone is tested! Skip to find a truly fresh zone.

    # 4. Entry Range Check (CMP must be near or inside zone)
    max_dz_entry = proximal * (1 + threshold)
    if distal <= cmp <= max_dz_entry:
      base_score = 2 if num_bases <= 3 else 1
      strength_score = 2 if has_gap_out else 1
      total_score = (
          3 + base_score + strength_score
      )  # 3 Points automatically for Fresh Zone

      dz_results.append({
          'type': 'DEMAND',
          'pattern': pattern,
          'proximal': round(proximal, 2),
          'distal': round(distal, 2),
          'dist_pct': round(((cmp - proximal) / proximal) * 100, 2),
          'bases': num_bases,
          'score': total_score,
          'has_gap': has_gap_out,
          'cmp': round(cmp, 2),
          'status': 'FRESH',
      })
      break  # Lock to the latest fresh Demand Zone for this timeframe

  return dz_results


def scan_stocks():
  symbols = get_nifty_500_symbols()
  print(
      f'Scanning Nifty 500 ({len(symbols)} stocks) for ACCURATE FRESH DEMAND'
      ' ZONES...'
  )

  timeframes = [
      'Daily',
      'Weekly',
      'Monthly',
      'Quarterly',
      'Half-Yearly',
      'Yearly',
  ]
  results = {tf: {'DZ': []} for tf in timeframes}

  for idx, symbol in enumerate(symbols):
    try:
      stock_name = symbol.replace('.NS', '')
      df_daily = yf.download(
          symbol, period='5y', interval='1d', progress=False
      )

      if df_daily.empty:
        continue

      # Clean pandas multi-indexing from yfinance downloads
      if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

      df_daily = df_daily.dropna()

      for tf in timeframes:
        df_tf = resample_data(df_daily, tf)
        dzs = find_fresh_demand_zones(df_tf, tf)

        for dz in dzs:
          dz['symbol'] = stock_name
          results[tf]['DZ'].append(dz)

      if (idx + 1) % 50 == 0:
        print(f'Processed {idx + 1}/{len(symbols)} stocks...')

    except Exception:
      continue

  with open('scan_results.json', 'w') as f:
    json.dump(results, f, indent=4)

  print(
      'Scan finished successfully! Saved fresh demand zones to'
      ' scan_results.json.'
  )


if __name__ == '__main__':
  scan_stocks()
