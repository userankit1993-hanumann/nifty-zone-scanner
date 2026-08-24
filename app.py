import json
import streamlit as st

st.set_page_config(page_title="Nifty 500 Demand Zone Scanner", layout="wide")

st.title("🟢 Nifty 500 — DEMAND ZONE SCANNER")
st.caption(
    "Automated GTF Strategy | Body-to-Wick Marking | 1 to 4 Base Candles | Gap"
    " Treatment | Fresh Zones Only"
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
      "⚠️ Scan data not found. Please trigger daily_scanner.py or run the GitHub"
      " Action workflow!"
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

      st.markdown(f"### 🟢 FRESH DEMAND ZONES — `{len(dz_list)} Stock(s) Found`")

      if dz_list:
        cols = st.columns(2)  # Two-column layout for clean viewing
        for col_idx, item in enumerate(dz_list):
          with cols[col_idx % 2]:
            gap_flag = "🚀 GAP OUT" if item.get("has_gap") else ""
            with st.container():
              st.success(
                  f"### **{item['symbol']}** | `{item['pattern']}` {gap_flag}\n"
                  f"• **Current Price (CMP):** ₹`{item.get('cmp', 'N/A')}`\n\n"
                  f"• **🟢 Proximal Line (Entry):** ₹`{item['proximal']}`\n\n"
                  f"• **🔴 Distal Line (StopLoss):** ₹`{item['distal']}`\n\n"
                  f"• **Distance to Zone:** `+{item['dist_pct']}%`\n\n"
                  f"• **Base Candles Count:** `{item['bases']} / 4`\n\n"
                  f"• **Trade Quality Score:** `{item['score']} / 7`"
              )
              st.divider()
      else:
        st.info(f"No fresh Demand Zones found near threshold for {tf}.")
