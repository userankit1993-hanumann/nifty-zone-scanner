import io
import json
import pandas as pd
import requests
import yfinance as yf

TIMEFRAME_THRESHOLDS = {
    'Daily': 0.03,
    'Weekly': 0.10,
    'Monthly': 0.12,
    'Quarterly': 0.12,
    'Half-Yearly': 0.12,
    'Yearly': 0.12,
}


def get_nifty_500_symbols():
  """Fetches full Nifty 500 list from official NSE sources with fallbacks."""
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
  except Exception as e:
    print(f'NSE CSV fetch failed: {e}. Trying Wikipedia...')

  try:
    wiki_url = 'https://en.wikipedia.org/wiki/NIFTY_500'
    tables = pd.read_html(wiki_url)
    for df in tables:
      for col in ['Symbol', 'Ticker']:
        if col in df.columns:
          return [
              f'{str(sym).strip()}.NS'
              for sym in df[col].dropna()
              if str(sym).strip()
          ]
  except Exception as e:
    print(f'Wikipedia fetch failed: {e}')

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
  """GTF Exciting Candle = Body > 50% of Range OR Gap Treatment"""
  c_open, c_high, c_low, c_close = (
      row['Open'],
      row['High'],
      row['Low'],
      row['Close'],
  )
  c_range = c_high - c_low
  if c_range == 0:
    return False, False

  body = abs(c_close - c_open)
  body_pct = body / c_range

  is_exciting = body_pct > 0.50
  has_gap = False

  if prev_row is not None:
    if c_open > prev_row['High'] or c_open < prev_row['Low']:
      has_gap = True
      is_exciting = True

  return is_exciting, has_gap


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


def is_zone_fresh(df, legout_idx, zone_type, proximal):
  """GTF Freshness Check: Ensures price has not entered/tested the zone between Leg-out and current bar"""
  subsequent_df = df.iloc[legout_idx + 1 :]
  if subsequent_df.empty:
    return True

  if zone_type == 'DEMAND':
    # If any subsequent low dropped into/below the proximal line, zone is tested
    if (subsequent_df['Low'] <= proximal).any():
      return False
  elif zone_type == 'SUPPLY':
    # If any subsequent high rose into/above the proximal line, zone is tested
    if (subsequent_df['High'] >= proximal).any():
      return False

  return True


def find_gtf_zones(df, timeframe):
  if len(df) < 10:
    return [], []

  cmp = float(df['Close'].iloc[-1])
  dz_results, sz_results = [], []

  found_dz = False
  found_sz = False

  # Look backward from recent bars to discover the LATEST formed zone first
  for i in range(len(df) - 2, max(len(df) - 60, 5), -1):
    legout_row = df.iloc[i]
    prev_row = df.iloc[i - 1]

    is_legout_ex, has_gap_out = is_exciting_candle(legout_row, prev_row)
    if not is_legout_ex:
      continue

    # Identify Base candles (1 to 5 max)
    base_indices = []
    b_idx = i - 1
    while b_idx >= 0:
      row = df.iloc[b_idx]
      p_row = df.iloc[b_idx - 1] if b_idx > 0 else None
      is_ex, _ = is_exciting_candle(row, p_row)
      if not is_ex:
        base_indices.append(b_idx)
        b_idx -= 1
        if len(base_indices) > 5:
          break
      else:
        break

    num_bases = len(base_indices)
    if num_bases < 1 or num_bases > 5:
      continue

    legin_idx = base_indices[-1] - 1
    if legin_idx < 0:
      continue

    legin_row = df.iloc[legin_idx]
    p_legin = df.iloc[legin_idx - 1] if legin_idx > 0 else None
    is_legin_ex, _ = is_exciting_candle(legin_row, p_legin)
    if not is_legin_ex:
      continue

    base_df = df.iloc[base_indices[::-1]]

    # 🟢 FRESH LATEST DEMAND ZONE (DZ)
    if legout_row['Close'] > legout_row['Open'] and not found_dz:
      pattern = 'RBR' if legin_row['Close'] > legin_row['Open'] else 'DBR'
      proximal = float(base_df[['Open', 'Close']].max().max())
      distal = float(base_df['Low'].min())

      # GTF Exception Rules
      if pattern == 'DBR' and float(legin_row['Low']) < distal:
        distal = float(legin_row['Low'])
      elif pattern == 'RBR' and float(legout_row['Low']) < distal:
        distal = float(legout_row['Low'])

      # Freshness Verification
      if is_zone_fresh(df, i, 'DEMAND', proximal):
        threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
        max_dz_entry = proximal * (1 + threshold)

        if distal <= cmp <= max_dz_entry:
          base_score = 2 if num_bases <= 3 else 1
          strength_score = 2 if has_gap_out else 1
          total_score = (
              3 + base_score + strength_score
          )  # 3 points for Fresh Zone

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
          found_dz = True  # Locks the LATEST fresh zone

    # 🔴 FRESH LATEST SUPPLY ZONE (SZ)
    elif legout_row['Close'] < legout_row['Open'] and not found_sz:
      pattern = 'DBD' if legin_row['Close'] < legin_row['Open'] else 'RBD'
      proximal = float(base_df[['Open', 'Close']].min().min())
      distal = float(base_df['High'].max())

      # GTF Exception Rules
      if pattern == 'RBD' and float(legout_row['High']) > distal:
        distal = float(legout_row['High'])
      elif pattern == 'DBD' and float(legin_row['High']) > distal:
        distal = float(legin_row['High'])

      # Freshness Verification
      if is_zone_fresh(df, i, 'SUPPLY', proximal):
        threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
        min_sz_entry = proximal * (1 - threshold)

        if min_sz_entry <= cmp <= distal:
          base_score = 2 if num_bases <= 3 else 1
          strength_score = 2 if has_gap_out else 1
          total_score = (
              3 + base_score + strength_score
          )  # 3 points for Fresh Zone

          sz_results.append({
              'type': 'SUPPLY',
              'pattern': pattern,
              'proximal': round(proximal, 2),
              'distal': round(distal, 2),
              'dist_pct': round(((proximal - cmp) / proximal) * 100, 2),
              'bases': num_bases,
              'score': total_score,
              'has_gap': has_gap_out,
              'cmp': round(cmp, 2),
              'status': 'FRESH',
          })
          found_sz = True  # Locks the LATEST fresh zone

    if found_dz and found_sz:
      break

  return dz_results, sz_results


def scan_stocks():
  symbols = get_nifty_500_symbols()
  print(f'Starting Fresh GTF Zone Scan for {len(symbols)} stocks...')

  timeframes = [
      'Daily',
      'Weekly',
      'Monthly',
      'Quarterly',
      'Half-Yearly',
      'Yearly',
  ]
  results = {tf: {'DZ': [], 'SZ': []} for tf in timeframes}

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
        dzs, szs = find_gtf_zones(df_tf, tf)

        for dz in dzs:
          dz['symbol'] = stock_name
          results[tf]['DZ'].append(dz)

        for sz in szs:
          sz['symbol'] = stock_name
          results[tf]['SZ'].append(sz)

      if (idx + 1) % 50 == 0:
        print(f'Processed {idx + 1}/{len(symbols)} stocks...')

    except Exception:
      continue

  with open('scan_results.json', 'w') as f:
    json.dump(results, f, indent=4)

  print('Scan complete! Saved latest fresh zones to scan_results.json.')


if __name__ == '__main__':
  scan_stocks()
