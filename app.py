import streamlit as st
import json
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Nifty Zone Classifier",
    page_icon="📈",
    layout="wide"
)

st.title("🎯 Daily Market Zone Classification (3:35 PM Scan)")

try:
    # Read the JSON file created by daily_scanner.py
    with open('scan_results.json', 'r') as f:
        data = json.load(f)
    
    st.caption(f"📅 Last Executed: **{data.get('last_updated', 'N/A')}**")
    results = data.get('results', [])

    if results:
        df = pd.DataFrame(results)

        tf_labels = {
            'D': 'Daily',
            'W': 'Weekly',
            'M': 'Monthly',
            'Q': 'Quarterly',
            'HY': 'Half-Yearly',
            'Y': 'Yearly'
        }

        # Create main tabs for each timeframe
        tabs = st.tabs([label for label in tf_labels.values()])

        for idx, (tf_code, tf_name) in enumerate(tf_labels.items()):
            with tabs[idx]:
                # Filter data for the specific timeframe
                tf_df = df[df['Timeframe'] == tf_code]
                
                if tf_df.empty:
                    st.info(f"No stocks approaching zones in the {tf_name} timeframe.")
                else:
                    col1, col2 = st.columns(2)

                    # Demand Zone Column
                    with col1:
                        st.subheader(f"🟢 {tf_name} Demand Zones (DZ)")
                        dz_df = tf_df[tf_df['Zone_Type'] == 'DZ']
                        if not dz_df.empty:
                            st.dataframe(
                                dz_df[['Symbol', 'Classification', 'CMP', 'Proximal', 'Distal']],
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.write("No Demand Zones found.")

                    # Supply Zone Column
                    with col2:
                        st.subheader(f"🔴 {tf_name} Supply Zones (SZ)")
                        sz_df = tf_df[tf_df['Zone_Type'] == 'SZ']
                        if not sz_df.empty:
                            st.dataframe(
                                sz_df[['Symbol', 'Classification', 'CMP', 'Proximal', 'Distal']],
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.write("No Supply Zones found.")
    else:
        st.info("No stocks approaching zones in the latest 3:35 PM scan.")

except FileNotFoundError:
    st.warning("No `scan_results.json` file found yet. Run `python daily_scanner.py` or trigger the GitHub Action to generate data.")