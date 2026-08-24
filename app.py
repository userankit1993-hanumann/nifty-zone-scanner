import streamlit as st
import json

st.set_page_config(page_title="Nifty 500 Zone Scanner", layout="wide")

st.title("📈 Nifty 500 Demand Zone & Gap Scanner")
st.caption("Updated daily at 3:35 PM IST | Daily (3%) | Weekly (10%) | Monthly/Quarterly/Half-Yearly/Yearly (12%)")

@st.cache_data(ttl=300)
def load_data():
    try:
        with open('scan_results.json', 'r') as f:
            return json.load(f)
    except Exception:
        return None

data = load_data()

if not data:
    st.warning("⚠️ Scanner data is initializing or running the first scan. Please run the workflow in GitHub Actions first!")
else:
    timeframes = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"]
    tabs = st.tabs(timeframes)

    for idx, tf in enumerate(timeframes):
        with tabs[idx]:
            dz_list = data.get(tf, {}).get("DZ", [])
            
            st.subheader(f"🟢 Demand Zone Stocks ({len(dz_list)})")
            
            if dz_list:
                for stock in dz_list:
                    # Support both list formats
                    if isinstance(stock, dict):
                        symbol = stock.get("symbol", "")
                        dist = stock.get("dist_pct", 0)
                        gap = stock.get("has_gap", False)
                        gap_badge = "🚀 **GAP UP**" if gap else "⚪ Normal"
                        st.markdown(f"• **{symbol}** — Distance from Low: `+{dist}%` | {gap_badge}")
                    else:
                        st.markdown(f"• **{stock}**")
            else:
                st.info(f"No stocks currently within the Demand Zone threshold for {tf}.")
