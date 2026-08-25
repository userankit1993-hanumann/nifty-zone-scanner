import json
import streamlit as st

st.set_page_config(page_title="Nifty 500 Fresh Demand Zone Scanner", layout="wide",  initial_sidebar_state="expanded",)

st.title("🟢 Nifty 500 — ACCURATE FRESH DEMAND ZONES")
st.caption(
    "GTF Strategy | Unadjusted Broker-Matching OHLC Data | Proximal: Open of"
    " Red / Close of Green Base Candle | Distal: Base Low (Leg-Out Exception"
    " Included) | 1 to 4 Bases"
)

# Sidebar Refresh Control
st.sidebar.header("Scanner Controls")
if st.sidebar.button("🔄 Refresh Display Data"):
  st.cache_data.clear()
  st.rerun()


@st.cache_data(ttl=300)
def load_data():
  try:
    with open("scan_results.json", "r") as f:
      return json.load(f)
  except Exception:
    return None


data = load_data()

if not data:
  st.warning(
      "⚠️ Scan data not found. Please execute daily_scanner.py locally or via"
      " GitHub Actions to generate scan_results.json!"
  )
else:
  timeframes = [
      "Daily",
      "Weekly",
      "Monthly",
      "Quarterly",
      "Half-Yearly",
      "Yearly",
  ]
  tabs = st.tabs(timeframes)

  for idx, tf in enumerate(timeframes):
    with tabs[idx]:
      dz_list = data.get(tf, {}).get("DZ", [])

      st.markdown(
          f"### 🟢 STRICTLY FRESH DEMAND ZONES — `{len(dz_list)} Stock(s)`"
      )

      if dz_list:
        cols = st.columns(2)
        for col_idx, item in enumerate(dz_list):
          with cols[col_idx % 2]:
            gap_flag = "🚀 GAP OUT" if item.get("has_gap") else ""
            with st.container():
              st.success(
                  f"### **{item['symbol']}** | Pattern: `{item['pattern']}`"
                  f" {gap_flag}\n\n"
                  f"• **Current Price (CMP):** ₹`{item.get('cmp', 'N/A')}`\n\n"
                  f"• **🟢 Proximal Line (Entry):** ₹`{item['proximal']}` *(Base"
                  " Body)*\n\n"
                  f"• **🔴 Distal Line (Stop Loss):** ₹`{item['distal']}`"
                  " *(Lowest Wick / Leg-Out Exception)*\n\n"
                  f"• **Distance to Proximal:** `+{item['dist_pct']}%`\n\n"
                  f"• **Base Candles Count:** `{item['bases']} / 4`\n\n"
                  f"• **Zone Status:** `FRESH (Untested)`\n\n"
                  f"• **Trade Quality Score:** `{item['score']} / 7`"
              )
              st.divider()
      else:
        st.info(f"No active, fresh Demand Zones found near threshold for {tf}.")
