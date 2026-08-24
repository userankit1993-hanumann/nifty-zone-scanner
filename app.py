import json
import streamlit as st

st.set_page_config(page_title="GTF Fresh Demand Zone Scanner", layout="wide")

st.title("🟢 Nifty 500 — FRESH DEMAND ZONE SCANNER")
st.caption(
    "Automated GTF Strategy | Backtested Freshness Check | Accurate"
    " Body-to-Wick Marking | 1 to 4 Base Candles | Gap-Up Treatment"
)


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
      "⚠️ Scan data not found. Please run daily_scanner.py or trigger the"
      " GitHub Action workflow!"
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
                  f"• **🟢 Proximal Line (Entry):** ₹`{item['proximal']}` *(Max"
                  " Base Body)*\n\n"
                  f"• **🔴 Distal Line (Stop Loss):** ₹`{item['distal']}`"
                  " *(Lowest Wick)*\n\n"
                  f"• **Distance to Proximal:** `+{item['dist_pct']}%`\n\n"
                  f"• **Base Candles Count:** `{item['bases']} / 4`\n\n"
                  f"• **Zone Status:** `FRESH (Untested)`\n\n"
                  f"• **Trade Quality Score:** `{item['score']} / 7`"
              )
              st.divider()
      else:
        st.info(f"No active, fresh Demand Zones near entry threshold for {tf}.")
