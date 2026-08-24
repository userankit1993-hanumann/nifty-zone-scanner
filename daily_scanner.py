import pandas as pd
import yfinance as yf
import json

# Full Nifty 500 Ticker List
NIFTY_500_SYMBOLS = [
    "3MINDIA.NS", "ABB.NS", "ACC.NS", "AIAENG.NS", "APLAPOLLO.NS", "AUBANK.NS", "AARTIDRUGS.NS",
    "AARTIIND.NS", "AAVAS.NS", "ABBOTINDIA.NS", "ACE.NS", "ADANIENSOL.NS", "ADANIENT.NS", "ADANIGREEN.NS",
    "ADANIPORTS.NS", "ADANIPOWER.NS", "ATGL.NS", "AWL.NS", "ABCAPITAL.NS", "ABFRL.NS", "AEGISCHEM.NS",
    "AFFLE.NS", "AJANTPHARM.NS", "APLLTD.NS", "ALKEM.NS", "ALKYLAMINE.NS", "ALLCARGO.NS", "ALOKINDS.NS",
    "ARE&M.NS", "AMBER.NS", "AMBUJACEM.NS", "ANANDRATHI.NS", "ANANGEL.NS", "ANGELONE.NS", "ANURAS.NS",
    "APARINDS.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "APTUS.NS", "ACI.NS", "ASAHIINDIA.NS", "ASHOKLEY.NS",
    "ASIANPAINT.NS", "ASTERDM.NS", "ASTRAZEN.NS", "ASTRAL.NS", "ATUL.NS", "AUROPHARMA.NS", "AVANTIFEED.NS",
    "DMART.NS", "AXISBANK.NS", "BASF.NS", "BSE.NS", "BAJAJ-AUTO.NS", "BAJAJELEC.NS", "BAJAJFINSV.NS",
    "BAJFINANCE.NS", "BAJAJHLDNG.NS", "BALAMINES.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS",
    "BANKBARODA.NS", "BANKINDIA.NS", "MAHABANK.NS", "BATAINDIA.NS", "BAYERCROP.NS", "BERGEPAINT.NS",
    "BDL.NS", "BEL.NS", "BHARATFORG.NS", "BHEL.NS", "BPCL.NS", "BHARTIARTL.NS", "BIOCON.NS", "BIRLACORPN.NS",
    "BSOFT.NS", "BLISSGVS.NS", "BLUEDART.NS", "BLUESTARCO.NS", "BBTC.NS", "BORORENEW.NS", "BOSCHLTD.NS",
    "BRIGADE.NS", "BRITANNIA.NS", "MAPMYINDIA.NS", "CCL.NS", "CESC.NS", "CGPOWER.NS", "CIEINDIA.NS",
    "CRISIL.NS", "CSBBANK.NS", "CAMPUS.NS", "CANFINHOME.NS", "CANBK.NS", "CGCL.NS", "CARBORUNIV.NS",
    "CASTROLIND.NS", "CEATLTD.NS", "CENTRALBK.NS", "CDSL.NS", "CENTURYPLY.NS", "CENTURYTEX.NS", "CERA.NS",
    "CHALET.NS", "CHAMBLFERT.NS", "CHEMCON.NS", "CHAMBAL.NS", "CHOLAHLDNG.NS", "CHOLAFIN.NS", "CIPLA.NS",
    "CUB.NS", "CLEAN.NS", "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "COLPAL.NS", "CAMS.NS",
    "CONCORDBIO.NS", "CONCOR.NS", "COROMANDEL.NS", "CRAFTSMAN.NS", "CREDITACC.NS", "CROMPTON.NS",
    "CUMMINSIND.NS", "CYIENT.NS", "DCMSHRIRAM.NS", "DLF.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS",
    "DELHIVERY.NS", "DEVYANI.NS", "DIVISLAB.NS", "DIXON.NS", "LALPATHLAB.NS", "DRREDDY.NS", "EIDPARRY.NS",
    "EIHOTEL.NS", "EPL.NS", "EASEMYTRIP.NS", "EICHERMOT.NS", "ELECON.NS", "ELGIEQUIP.NS", "EMAMILTD.NS",
    "ENDURANCE.NS", "ENGINERSIN.NS", "EQUITASBNK.NS", "ERIS.NS", "ESCORTS.NS", "EXIDEIND.NS", "FDC.NS",
    "NYKAA.NS", "FEDERALBNK.NS", "FACT.NS", "FINEORG.NS", "FINPIPE.NS", "FSN.NS", "FIVESTAR.NS",
    "FORTIS.NS", "GRINFRA.NS", "GAIL.NS", "GMMPFAUDLR.NS", "GMRINFRA.NS", "GALAXYSURF.NS", "GARFIBRES.NS",
    "GATEWAY.NS", "GEPIL.NS", "GHCL.NS", "GICRE.NS", "GILLETTE.NS", "GLAND.NS", "GLAXO.NS", "GLENMARK.NS",
    "MEDANTA.NS", "GOCOLORS.NS", "GODFRYPHLP.NS", "GODREJAGRO.NS", "GODREJCP.NS", "GODREJIND.NS",
    "GODREJPROP.NS", "GRANULES.NS", "GRAPHITE.NS", "GRASIM.NS", "GREATSHEship.NS", "GESHIP.NS", "GRINDWELL.NS",
    "GAEL.NS", "FLUOROCHEM.NS", "GUJGASLTD.NS", "GNFC.NS", "GPPL.NS", "GSFC.NS", "GSPL.NS", "HEG.NS",
    "HCLTECH.NS", "HDFCAMC.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HFCL.NS", "HLEGLAS.NS", "HAL.NS",
    "HAPPSTMNDS.NS", "HAVELLS.NS", "HEROMOTOCO.NS", "HIMATSEIDE.NS", "HINDALCO.NS", "HALDYN.NS", "HCOPPER.NS",
    "HINDPETRO.NS", "HINDUNILVR.NS", "HINDZINC.NS", "POWERINDIA.NS", "HOMEFIRST.NS", "HONAUT.NS",
    "HUDCO.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "ISEC.NS", "IDBI.NS", "IDFCFIRSTB.NS",
    "IDFC.NS", "IFCI.NS", "IIFL.NS", "IIFLSEC.NS", "IRB.NS", "IRCON.NS", "ITC.NS", "ITI.NS", "INDIACEM.NS",
    "INDIAMART.NS", "INDIANB.NS", "IEX.NS", "INDHOTEL.NS", "IOC.NS", "IOB.NS", "IRCTC.NS", "IRFC.NS",
    "INDIGOPNTS.NS", "IGL.NS", "INDUSTOWER.NS", "INDUSINDBK.NS", "NAUKRI.NS", "INFY.NS", "INOXWIND.NS",
    "INTELLECT.NS", "INDIGO.NS", "IPCALAB.NS", "JBCHEPHARM.NS", "JBMA.NS", "JKCEMENT.NS", "JKLAKSHMI.NS",
    "JKPAPER.NS", "JMFINANCIL.NS", "JSWENERGY.NS", "JSWINFRA.NS", "JSWSTEEL.NS", "JAMNAAUTO.NS",
    "JINDALSAW.NS", "JINDALSTEL.NS", "JIOFIN.NS", "JUBLFOOD.NS", "JUBLINGREA.NS", "JUBLPHARMA.NS",
    "JUSTDIAL.NS", "JYOTHYLAB.NS", "KPRMILL.NS", "KEI.NS", "KNRCON.NS", "KPITTECH.NS", "KRBL.NS",
    "KSB.NS", "KAJARIACER.NS", "KPIL.NS", "KALYANKJIL.NS", "KANSAINER.NS", "KARURVYSYA.NS", "KEC.NS",
    "KENNAMET.NS", "KOTAKBANK.NS", "KIMS.NS", "L&TFH.NS", "LTTS.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS",
    "LATENTVIEW.NS", "LAURUSLABS.NS", "LXCHEM.NS", "LEMONTREE.NS", "LICI.NS", "LINDEINDIA.NS", "LLOYDSME.NS",
    "LUPIN.NS", "MMTC.NS", "MRF.NS", "MTARTECH.NS", "LODHA.NS", "MGL.NS", "MAHSEAMLES.NS", "M&MFIN.NS",
    "M&M.NS", "MHRIL.NS", "MAHLIFE.NS", "MANAPPURAM.NS", "MRPL.NS", "MARICO.NS", "MARUTI.NS", "MASTEK.NS",
    "MFSL.NS", "MAXHEALTH.NS", "MAZDOCK.NS", "MEDPLUS.NS", "METROPOLIS.NS", "MINDACORP.NS", "MSUMI.NS",
    "MOTILALOFS.NS", "MPHASIS.NS", "MCX.NS", "MUTHOOTFIN.NS", "NATCOPHARM.NS", "NBCC.NS", "NCC.NS",
    "NHPC.NS", "NLCINDIA.NS", "NMDC.NS", "NOCIL.NS", "NTPC.NS", "NH.NS", "NATIONALUM.NS", "NAVINFLUOR.NS",
    "NAZARA.NS", "NESTLEIND.NS", "NETWORK18.NS", "NAM-INDIA.NS", "NUVAMA.NS", "NUVOCO.NS", "OBEROIRLTY.NS",
    "ONGC.NS", "OIL.NS", "OLECTRA.NS", "PAYTM.NS", "OFSS.NS", "POLICYBZR.NS", "PCBL.NS", "PIIND.NS",
    "PNBHOUSING.NS", "PNCINFRA.NS", "PVRINOX.NS", "PAGEIND.NS", "PATANJALI.NS", "PERSISTENT.NS", "PETRONET.NS",
    "PFIZER.NS", "PHOENIXLTD.NS", "PIDILITIND.NS", "PEL.NS", "PPLPHARMA.NS", "POLYMED.NS", "POLYCAB.NS", "POONAWALLA.NS",
    "PFC.NS", "POWERGRID.NS", "PRAJIND.NS", "PRESTIGE.NS", "PRINCEPIPE.NS", "PRSMJOHNSN.NS", "PGHL.NS",
    "PGINVIT.NS", "PNB.NS", "QUESS.NS", "RBLBANK.NS", "RECLTD.NS", "RHIM.NS", "RITES.NS", "RADICO.NS",
    "RVNL.NS", "RAILTEL.NS", "RAIN.NS", "RAINBOW.NS", "RAJESHEXPO.NS", "RALLIS.NS", "RAMCOCEM.NS",
    "RAMKRASN.NS", "RCF.NS", "RATNAMANI.NS", "RTNINDIA.NS", "RAYMOND.NS", "REDINGTON.NS", "RELIANCE.NS",
    "RELIGARE.NS", "RBA.NS", "ROSSARI.NS", "ROUTE.NS", "SBFC.NS", "SBICARD.NS", "SBILIFE.NS", "SJVN.NS",
    "SKFINDIA.NS", "SRF.NS", "SAFARI.NS", "MOTHERSON.NS", "SANGHIIND.NS", "SANOFI.NS", "SAPPHIRE.NS",
    "SAREGAMA.NS", "SCHAEFFLER.NS", "SCHNEIDER.NS", "SEAMECLTD.NS", "SHARDACROP.NS", "SFL.NS", "SHLOK.NS",
    "SHREECEM.NS", "RENUKA.NS", "SHRIRAMFIN.NS", "SHRIRAMPPN.NS", "SIEMENS.NS", "SOBHA.NS", "SOLARINDS.NS",
    "SONACOMS.NS", "SONATSOFTW.NS", "SOUTHBANK.NS", "STARHEALTH.NS", "SBIN.NS", "SAIL.NS", "SWSOLAR.NS", "SUMICHEM.NS",
    "SPARC.NS", "SUNPHARMA.NS", "SUNTV.NS", "SUNDARMFIN.NS", "SUNDRMFAST.NS", "SUNTECK.NS", "SUPRAJIT.NS",
    "SUPREMEIND.NS", "SUVENPHAR.NS", "SUZLON.NS", "SYMPHONY.NS", "SYNGENE.NS", "TVSMOTOR.NS", "TVSSRICHAK.NS",
    "TANLA.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAMTRDVR.NS", "TATAMOTORS.NS",
    "TATAPOWER.NS", "TATASTEEL.NS", "TATATECH.NS", "TTML.NS", "TCS.NS", "TECHM.NS", "TEJASNET.NS",
    "NIACL.NS", "RAMCOIND.NS", "THERMAX.NS", "THYROCARE.NS", "TIINDIA.NS", "TIMKEN.NS", "TITAN.NS",
    "TORNTPHARM.NS", "TORNTPOWER.NS", "TRENT.NS", "TRIDENT.NS", "TRITURBINE.NS", "TRIVENI.NS", "UGROCAP.NS",
    "UBOOK.NS", "UCOBANK.NS", "UNOMINDA.NS", "UPL.NS", "UTIAMC.NS", "ULTRACEMCO.NS", "UNIONBANK.NS",
    "UBL.NS", "MCDOWELL-N.NS", "VGUARD.NS", "VMART.NS", "VIPIND.NS", "VAIBHAVGBL.NS", "VTL.NS", "VARROC.NS",
    "VBL.NS", "MANYAVAR.NS", "VEDL.NS", "VENKEYS.NS", "VIJAYA.NS", "VINATIORGA.NS", "IDEA.NS", "VOLTAS.NS",
    "WELCORP.NS", "WELSPUNLIV.NS", "WESTLIFE.NS", "WHIRLPOOL.NS", "WIPRO.NS", "WOCKPHARMA.NS", "YESBANK.NS",
    "ZEEL.NS", "ZENSARTECH.NS", "ZOMATO.NS", "ZYDUSLIFE.NS", "ECLERX.NS"
]

TIMEFRAME_THRESHOLDS = {
    'Daily': 0.03,        # 3%
    'Weekly': 0.10,       # 10%
    'Monthly': 0.12,      # 12%
    'Quarterly': 0.12,    # 12%
    'Half-Yearly': 0.12,  # 12%
    'Yearly': 0.12        # 12%
}

def analyze_zone_and_gap(df, timeframe):
    """Calculates proximity to demand zone and verifies gap formation"""
    if len(df) < 5:
        return None
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    latest_close = float(df['Close'].iloc[-1])
    latest_open = float(df['Open'].iloc[-1])
    prev_high = float(df['High'].iloc[-2])
    
    demand_base = float(df['Low'].tail(10).min())
    threshold_pct = TIMEFRAME_THRESHOLDS.get(timeframe, 0.05)
    
    max_dz_price = demand_base * (1 + threshold_pct)
    
    if demand_base <= latest_close <= max_dz_price:
        has_gap = latest_open > prev_high
        dist_from_dz = round(((latest_close - demand_base) / demand_base) * 100, 2)
        
        return {
            "in_dz": True,
            "has_gap": has_gap,
            "distance_pct": dist_from_dz
        }
    return None

def resample_data(df, timeframe):
    rule_map = {
        'Daily': 'D',
        'Weekly': 'W',
        'Monthly': 'ME',
        'Quarterly': '3ME',
        'Half-Yearly': '6ME',
        'Yearly': 'YE'
    }
    rule = rule_map.get(timeframe, 'D')
    try:
        return df.resample(rule).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()
    except Exception:
        fallback_map = {'Monthly': 'M', 'Quarterly': '3M', 'Half-Yearly': '6M', 'Yearly': 'Y'}
        return df.resample(fallback_map.get(timeframe, rule)).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()

def scan_nifty_500():
    print("Scanning full Nifty 500 list across all timeframes...")
    
    results = {
        "Daily": {"DZ": []},
        "Weekly": {"DZ": []},
        "Monthly": {"DZ": []},
        "Quarterly": {"DZ": []},
        "Half-Yearly": {"DZ": []},
        "Yearly": {"DZ": []}
    }
    
    # Fast download all 500 tickers in parallel
    data = yf.download(NIFTY_500_SYMBOLS, period="3y", interval="1d", group_by="ticker", progress=False)
    timeframes = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly']

    for symbol in NIFTY_500_SYMBOLS:
        try:
            stock_name = symbol.replace('.NS', '')
            if symbol in data:
                df_daily = data[symbol].dropna()
                if df_daily.empty:
                    continue
            else:
                continue

            for tf in timeframes:
                df_tf = resample_data(df_daily, tf)
                zone_info = analyze_zone_and_gap(df_tf, tf)
                
                if zone_info and zone_info["in_dz"]:
                    results[tf]["DZ"].append({
                        "symbol": stock_name,
                        "dist_pct": zone_info["distance_pct"],
                        "has_gap": zone_info["has_gap"]
                    })
        except Exception:
            continue

    with open('scan_results.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print("Nifty 500 scan complete. JSON saved successfully.")

if __name__ == "__main__":
    scan_nifty_500()
