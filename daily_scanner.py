import io
import json
import pandas as pd
import requests
import yfinance as yf

TIMEFRAME_THRESHOLDS = {
    'Daily': 0.05,
    'Weekly': 0.10,
    'Monthly': 0.15,
    'Quarterly': 0.15,
    'Half-Yearly': 0.15,
    'Yearly': 0.15,
}

# Scaled lookback limits per timeframe to prevent ghost zones from decades ago
MAX_LOOKBACK = {
    'Daily': 60,
    'Weekly': 52,
    'Monthly': 36,
    'Quarterly': 20,
    'Half-Yearly': 16,
    'Yearly': 10,
}


def get_nifty_500_symbols():
  url = 'https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv'
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      )
  }
  try:
    resp = requests.get(url, headers=headers, timeout=12)
    if resp.status_code == 200:
      df = pd.read_csv(io.StringIO(resp.text))
      if 'Symbol' in df.columns:
        return [f'{sym.strip()}.NS' for sym in df['Symbol'].dropna()]
  except Exception:
    pass
  return [
      'AIAENG.NS',
      'CIEINDIA.NS',
      'RELIANCE.NS',
      'TCS.NS',
      'HDFCBANK.NS',
      'INFY.NS',
      'ICICIBANK.NS',
  ]


def is_exciting_candle(row, prev_row=None):
  c_open = float(row['Open'])
  c_high = float(row['High'])
  c_low = float(row['Low'])
  c_close = float(row['Close'])
  body = abs(c_close - c_open)

  if prev_row is not None and c_open > float(prev_row['High']):
    gap_range = c_high - float(prev_row['High'])
    if gap_range > 0 and (body / gap_range) >= 0.50:
      return True, True

  candle_range = c_high - c_low
  if candle_range == 0:
    return False, False

  return (body / candle_range) > 0.50, False


def resample_gtf_exact(df, timeframe):
  """Strict exchange-aligned resampling for Weekly, Monthly, Quarterly, Half-Yearly, and Yearly."""
  if timeframe == 'Daily':
    return df

  df_copy = df.copy()
  if not isinstance(df_copy.index, pd.DatetimeIndex):
    df_copy.index = pd.to_datetime(df_copy.index)

  if timeframe == 'Weekly':
    # Resample weekly ending on Friday
    res = df_copy.resample('W-FRI').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    )
  elif timeframe == 'Monthly':
    # Resample by exact calendar month
    res = df_copy.resample('MS').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    )
  elif timeframe == 'Quarterly':
    # Resample by standard Financial Quarters (Jan, Apr, Jul, Oct starts)
    res = df_copy.resample('QS-JAN').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    )
  elif timeframe == 'Half-Yearly':
    # Custom grouping for Half-Yearly (Jan-Jun, Jul-Dec)
    df_copy['HY_Group'] = (
        df_copy.index.year.astype(str)
        + '_H'
        + ((df_copy.index.month - 1) // 6 + 1).astype(str)
    )
    res = df_copy.groupby('HY_Group').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    )
  elif timeframe == 'Yearly':
    # Resample by exact calendar year
    res = df_copy.resample('YS').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    )
  else:
    res = df_copy

  return res.dropna()


def is_demand_zone_fresh(df, legout_idx, proximal):
  subsequent_candles = df.iloc[legout_idx + 1 :]
  if subsequent_candles.empty:
    return True
  return float(subsequent_candles['Low'].min()) > proximal


def find_fresh_demand_zones(df, timeframe):
  if len(df) < 6:
    return []

  cmp = float(df['Close'].iloc[-1])
  threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
  max_back = MAX_LOOKBACK.get(timeframe, 20)
  dz_results = []

  # Iterate backwards using scaled lookback limits
  for i in range(len(df) - 2, max(len(df) - max_back, 2), -1):
    legout_row = df.iloc[i]
    prev_row = df.iloc[i - 1]

    # Leg-Out MUST be GREEN for Demand Zone
    if float(legout_row['Close']) <= float(legout_row['Open']):
      continue

    is_legout_ex, has_gap_out = is_exciting_candle(legout_row, prev_row)
    if not is_legout_ex:
      continue

    base_indices = []
    b_idx = i - 1
    while b_idx >= 0:
      row = df.iloc[b_idx]
      p_row = df.iloc[b_idx - 1] if b_idx > 0 else None
      is_ex, _ = is_exciting_candle(row, p_row)

      if not is_ex:
        base_indices.append(b_idx)
        b_idx -= 1
        if len(base_indices) > 4:
          break
      else:
        break

    num_bases = len(base_indices)
    if num_bases < 1 or num_bases > 4:
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
    pattern = (
        'RBR'
        if float(legin_row['Close']) > float(legin_row['Open'])
        else 'DBR'
    )

    # ACCURATE MARKINGS:
    # 1. Proximal: Top body level of base candles
    base_bodies = base_df[['Open', 'Close']].values.flatten()
    proximal = float(max(base_bodies))

    # 2. Distal: Minimum low of base candles
    distal = float(base_df['Low'].min())

    # 3. Leg-Out Exception Check ONLY
    if float(legout_row['Low']) < distal:
      distal = float(legout_row['Low'])

    if proximal <= distal:
      continue

    if not is_demand_zone_fresh(df, i, proximal):
      continue

    max_dz_entry = proximal * (1 + threshold)
    if distal <= cmp <= max_dz_entry:
      dz_results.append({
          'type': 'DEMAND',
          'pattern': pattern,
          'proximal': round(proximal, 2),
          'distal': round(distal, 2),
          'dist_pct': round(((cmp - proximal) / proximal) * 100, 2),
          'bases': num_bases,
          'score': 3
          + (2 if num_bases <= 3 else 1)
          + (2 if has_gap_out else 1),
          'has_gap': has_gap_out,
          'cmp': round(cmp, 2),
          'status': 'FRESH',
      })
      break

  return dz_results


def scan_stocks():
  symbols = get_nifty_500_symbols()
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
          symbol, period='10y', interval='1d', auto_adjust=False, progress=False
      )
      if df_daily.empty:
        continue

      if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily = df_daily.droplevel(1, axis=1)

      df_daily = df_daily[['Open', 'High', 'Low', 'Close']].dropna()

      for tf in timeframes:
        df_tf = resample_gtf_exact(df_daily, tf)
        dzs = find_fresh_demand_zones(df_tf, tf)
        for dz in dzs:
          dz['symbol'] = stock_name
          results[tf]['DZ'].append(dz)
    except Exception:
      continue

  with open('scan_results.json', 'w') as f:
    json.dump(results, f, indent=4)
  print('Updated accurately.')


if __name__ == '__main__':
  scan_stocks()
