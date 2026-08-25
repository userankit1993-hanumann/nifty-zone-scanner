import json
import pandas as pd
import yfinance as yf

# NSE Sectoral & Broad Market Indices
NIFTY_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY INFRA": "^CNXINFRA",
    "NIFTY COMMODITIES": "^CNXCMDT",
    "NIFTY PSE": "^CNXPSE",
    "NIFTY PSU BANK": "^CNXPSU",
    "NIFTY MIDCAP 100": "^NSEMDCP50",
}

TIMEFRAME_THRESHOLDS = {
    "Daily": 0.01,
    "Weekly": 0.02,
    "Monthly": 0.02,
    "Quarterly": 0.03,
    "Half-Yearly": 0.03,
    "Yearly": 0.03,
}

MAX_LOOKBACK = {
    "Daily": 60,
    "Weekly": 52,
    "Monthly": 36,
    "Quarterly": 20,
    "Half-Yearly": 16,
    "Yearly": 10,
}


def is_exciting_candle(row, prev_row=None):
  c_open, c_high, c_low, c_close = (
      float(row["Open"]),
      float(row["High"]),
      float(row["Low"]),
      float(row["Close"]),
  )
  body = abs(c_close - c_open)
  if prev_row is not None and c_open > float(prev_row["High"]):
    gap_range = c_high - float(prev_row["High"])
    if gap_range > 0 and (body / gap_range) >= 0.50:
      return True, True
  candle_range = c_high - c_low
  if candle_range == 0:
    return False, False
  return (body / candle_range) > 0.50, False


def resample_gtf_exact(df, timeframe):
  if timeframe == "Daily":
    return df
  df_copy = df.copy()
  if not isinstance(df_copy.index, pd.DatetimeIndex):
    df_copy.index = pd.to_datetime(df_copy.index)

  if timeframe == "Weekly":
    return df_copy.resample("W-FRI").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
  elif timeframe == "Monthly":
    return df_copy.resample("MS").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
  elif timeframe == "Quarterly":
    return df_copy.resample("QS-JAN").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
  elif timeframe == "Half-Yearly":
    df_copy["HY_Group"] = (
        df_copy.index.year.astype(str)
        + "_H"
        + ((df_copy.index.month - 1) // 6 + 1).astype(str)
    )
    return df_copy.groupby("HY_Group").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
  elif timeframe == "Yearly":
    return df_copy.resample("YS").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
  return df_copy


def find_fresh_zones(df, timeframe):
  if len(df) < 6:
    return []

  cmp = float(df["Close"].iloc[-1])
  threshold = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
  max_back = MAX_LOOKBACK.get(timeframe, 20)
  results = []

  for i in range(len(df) - 2, max(len(df) - max_back, 2), -1):
    legout_row, prev_row = df.iloc[i], df.iloc[i - 1]
    if float(legout_row["Close"]) <= float(legout_row["Open"]):
      continue

    is_legout_ex, has_gap_out = is_exciting_candle(legout_row, prev_row)
    if not is_legout_ex:
      continue

    base_indices = []
    b_idx = i - 1
    while b_idx >= 0:
      is_ex, _ = is_exciting_candle(
          df.iloc[b_idx], df.iloc[b_idx - 1] if b_idx > 0 else None
      )
      if not is_ex:
        base_indices.append(b_idx)
        b_idx -= 1
        if len(base_indices) > 4:
          break
      else:
        break

    if len(base_indices) < 1 or len(base_indices) > 4:
      continue

    legin_idx = base_indices[-1] - 1
    if legin_idx < 0:
      continue

    is_legin_ex, _ = is_exciting_candle(
        df.iloc[legin_idx], df.iloc[legin_idx - 1] if legin_idx > 0 else None
    )
    if not is_legin_ex:
      continue

    base_df = df.iloc[base_indices[::-1]]
    pattern = (
        "RBR"
        if float(df.iloc[legin_idx]["Close"]) > float(df.iloc[legin_idx]["Open"])
        else "DBR"
    )

    base_bodies = base_df[["Open", "Close"]].values.flatten()
    proximal = float(max(base_bodies))
    distal = float(base_df["Low"].min())

    if float(legout_row["Low"]) < distal:
      distal = float(legout_row["Low"])

    if proximal <= distal:
      continue

    subsequent = df.iloc[i + 1 :]
    if not subsequent.empty and float(subsequent["Low"].min()) <= proximal:
      continue

    if distal <= cmp <= (proximal * (1 + threshold)):
      results.append({
          "pattern": pattern,
          "proximal": round(proximal, 2),
          "distal": round(distal, 2),
          "dist_pct": round(((cmp - proximal) / proximal) * 100, 2),
          "bases": len(base_indices),
          "has_gap": has_gap_out,
          "cmp": round(cmp, 2),
      })
      break

  return results


def run_sector_scan():
  timeframes = [
      "Daily",
      "Weekly",
      "Monthly",
      "Quarterly",
      "Half-Yearly",
      "Yearly",
  ]
  results = {tf: [] for tf in timeframes}

  for name, ticker in NIFTY_INDICES.items():
    try:
      df = yf.download(
          ticker, period="10y", interval="1d", auto_adjust=False, progress=False
      )
      if df.empty:
        continue
      if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)

      df = df[["Open", "High", "Low", "Close"]].dropna()

      for tf in timeframes:
        df_tf = resample_gtf_exact(df, tf)
        zones = find_fresh_zones(df_tf, tf)
        for z in zones:
          z["symbol"] = name
          results[tf].append(z)
    except Exception:
      continue

  # Saves to a separate JSON file so scan_results.json is not touched
  with open("sector_results.json", "w") as f:
    json.dump(results, f, indent=4)

  print("Sector scan complete. Saved to sector_results.json.")


if __name__ == "__main__":
  run_sector_scan()
