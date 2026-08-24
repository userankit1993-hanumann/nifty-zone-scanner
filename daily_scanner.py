import io
import json
import pandas as pd
import requests
import yfinance as yf

# Timeframe Thresholds (Nearness to CMP)
TIMEFRAME_THRESHOLDS = {
    'Daily': 0.03,
    'Weekly': 0.10,
    'Monthly': 0.12,
    'Quarterly': 0.12,
    'Half-Yearly': 0.12,
    'Yearly': 0.12,
}


def get_nifty_500_symbols():
  """Fetches full Nifty 500 ticker list from official NSE source with fallbacks."""
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
  """Checks if Body > 50% of Candle Range.

  Includes GAP TREATMENT: If Gap-Up occurs, total range extends from previous
  high to current high. If Body >= 50% of this total gap range, it is an
  Exciting Candle.
  """
  c_open, c_high, c_low, c_close = (
      row['Open'],
      row['High'],
      row['Low'],
      row['Close'],
  )
  body = abs(c_close - c_open)

  # Check Gap-Up Condition
  if prev_row is not None and c_open > prev_row['High']:
    total_range_with_gap = c_high - prev_row['High']
    if total_range_with_gap > 0 and (body / total_range_with_gap) >= 0.50:
      return True, True  # (is_exciting, has_gap)

  # Standard Range Condition
  candle_range = c_high - c_low
  if candle_range == 0:
    return False, False

  is_exciting = (body / candle_range) > 0.50
  return is_exciting, False


def resample_data(df, timeframe):
  rule_map = {
      'Daily': 'D',
      'Weekly': 'W',
      'Monthly': 'ME',
      'Quarterly': '3ME',
      'Half-Yearly': '6ME',
      'Yearly': 'YE',
  }
  rule = rule_map.get(timeframe, 'D')
  try:
    return (
        df.resample(rule)
        .agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        .dropna()
    )
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


def is_zone_fresh(df, legout_idx, proximal):
  """Freshness Check: Ensures price has not dropped below/into proximal line after zone formation."""
  subsequent_df = df.iloc[legout_idx + 1 :]
  if subsequent_df.empty:
    return True
  return not (subsequent_df['Low'] <= proximal).any()


def find_demand_zones(df, timeframe):
  """DEMAND ZONES ONLY SCANNER Rules:

  - Leg-Out MUST be GREEN (Close > Open) and EXCITING (>50% body)
  - Base Candles: 1 to 4 MAX (Body <= 50%)
  - Leg-In MUST be EXCITING (>50% body)
  - Patterns: DBR (Drop-Base-Rally) or RBR (Rally-Base-Rally)
  """
  if len(df) < 10:
    return []

  cmp = float(df['Close'].iloc[-1])
  threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
  dz_results = []

  # Search backward from recent bars to find the LATEST demand zone
  for i in range(len(df) - 2, max(len(df) - 60, 5), -1):
    legout_row = df.iloc[i]
    prev_row = df.iloc[i - 1]

    # Leg-Out MUST be GREEN for Demand Zone
    if legout_row['Close'] <= legout_row['Open']:
      continue

    is_legout_ex, has_gap_out = is_exciting_candle(legout_row, prev_row)
    if not is_legout_ex:
      continue

    # Identify Base Candles (Strictly 1 to 4 Candles)
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
    if num_bases < 1 or num_bases > 4:  # Enforce 1-4 bases rule
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

    # Pattern Identification
    pattern = 'RBR' if legin_row['Close'] > legin_row['Open'] else 'DBR'

    # Zone Markings (Body-to-Wick Marking for Demand Zones)
    proximal = float(base_df[['Open', 'Close']].max().max())
    distal = float(base_df['Low'].min())

    # GTF Exception Adjustments for Distal Line
    if pattern == 'DBR' and float(legin_row['Low']) < distal:
      distal = float(legin_row['Low'])
    elif pattern == 'RBR' and float(legout_row['Low']) < distal:
      distal = float(legout_row['Low'])

    max_dz_entry = proximal * (1 + threshold)

    # Check Entry Range & Freshness
    if distal <= cmp <= max_dz_entry and is_zone_fresh(df, i, proximal):
      base_score = 2 if num_bases <= 3 else 1
      strength_score = 2 if has_gap_out else 1

      dz_results.append({
          'type': 'DEMAND',
          'pattern': pattern,
          'proximal': round(proximal, 2),
          'distal': round(distal, 2),
          'dist_pct': round(((cmp - proximal) / proximal) * 100, 2),
          'bases': num_bases,
          'score': 3 + base_score + strength_score,
          'has_gap': has_gap_out,
          'cmp': round(cmp, 2),
      })
      break  # Lock latest fresh Demand Zone

  return dz_results


def scan_stocks():
  symbols = get_nifty_500_symbols()
  print(f'Scanning Nifty 500 ({len(symbols)} stocks) for DEMAND ZONES ONLY...')

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

      if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

      df_daily = df_daily.dropna()

      for tf in timeframes:
        df_tf = resample_data(df_daily, tf)
        dzs = find_demand_zones(df_tf, tf)

        for dz in dzs:
          dz['symbol'] = stock_name
          results[tf]['DZ'].append(dz)

      if (idx + 1) % 50 == 0:
        print(f'Processed {idx + 1}/{len(symbols)} stocks...')

    except Exception:
      continue

  with open('scan_results.json', 'w') as f:
    json.dump(results, f, indent=4)

  print('Demand Zone Scan Finished Successfully!')


if __name__ == '__main__':
  scan_stocks()
