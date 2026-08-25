import json
import streamlit as st

st.set_page_config(page_title="Nifty Sector Indices Zones", layout="wide")

st.title("📈 NIFTY SECTOR INDICES — DEMAND & SUPPLY ZONES")
st.caption(
    "Trading Calendar Resampled | Fresh Zones Only | Gap Adjusted Proximal Lines"
)


@st.cache_data(ttl=60)
def load_sector_data():
  try:
    with open("sector_results.json", "r") as f:
      return json.load(f)
  except Exception:
    return None


sector_data = load_sector_data()

if not sector_data:
  st.warning(
      "⚠️ No sector scan results found. Please trigger the Sector Scanner"
      " workflow!"
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
      tf_data = sector_data.get(tf, {"DZ": [], "SZ": []})
      dz_list = tf_data.get("DZ", [])
      sz_list = tf_data.get("SZ", [])

      st.markdown(
          f"### `{tf}` Timeframe: `{len(dz_list)}` Demand Zones |"
          f" `{len(sz_list)}` Supply Zones"
      )

      col_dz, col_sz = st.columns(2)

      # DEMAND ZONES (GREEN)
      with col_dz:
        st.subheader("🟢 Fresh Demand Zones")
        if dz_list:
          for item in dz_list:
            gap_flag = (
                "🚀 GAP ADJUSTED" if item.get("gap_adjusted") else ""
            )
            st.success(
                f"### **{item['symbol']}** | `{item['pattern']}` {gap_flag}\n\n"
                f"• **Status:** `{item['freshness']}`\n\n"
                f"• **CMP:** ₹`{item['cmp']}`\n\n"
                f"• **🟢 Proximal Line (Entry):** ₹`{item['proximal']}`\n\n"
                f"• **🔴 Distal Line (Stop Loss):** ₹`{item['distal']}`\n\n"
                f"• **Distance to Entry:** `+{item['dist_pct']}%`\n\n"
                f"• **Base Candles:** `{item['bases']} / 4`"
            )
        else:
          st.info(f"No fresh Demand Zones found for {tf}.")

      # SUPPLY ZONES (RED)
      with col_sz:
        st.subheader("🔴 Fresh Supply Zones")
        if sz_list:
          for item in sz_list:
            gap_flag = (
                "🚀 GAP ADJUSTED" if item.get("gap_adjusted") else ""
            )
            st.error(
                f"### **{item['symbol']}** | `{item['pattern']}` {gap_flag}\n\n"
                f"• **Status:** `{item['freshness']}`\n\n"
                f"• **CMP:** ₹`{item['cmp']}`\n\n"
                f"• **🔴 Proximal Line (Entry):** ₹`{item['proximal']}`\n\n"
                f"• **🟢 Distal Line (Stop Loss):** ₹`{item['distal']}`\n\n"
                f"• **Distance to Entry:** `-{item['dist_pct']}%`\n\n"
                f"• **Base Candles:** `{item['bases']} / 4`"
            )
        else:
          st.info(f"No fresh Supply Zones found for {tf}.")
