from __future__ import annotations

# Ticker Library: Top global companies for diversified research
# SP500: Top 200 by Market Cap / Influence
# EUROPE: Top 100 (STOXX 100 approach)
# HK: Top 100 Hang Seng approach

SP500_TOP_200 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK.B", "TSLA", "V", "JPM",
    "LLY", "UNH", "MA", "AVGO", "XOM", "JNJ", "HD", "PG", "COST", "ABBV",
    "ADBE", "CRM", "AMD", "WMT", "CVX", "BAC", "PEP", "KO", "NFLX", "TMO",
    "ACN", "ABT", "LIN", "ORCL", "DIS", "MCD", "CSCO", "INTU", "MRK", "DHR",
    "VZ", "CMCSA", "TXN", "AMAT", "PFE", "PM", "CAT", "HON", "IBM", "NEE",
    "AMGN", "UNP", "INTC", "QCOM", "LOW", "SPGI", "GE", "ISRG", "NOW", "AXP",
    "DE", "PLD", "ELV", "SYK", "BKNG", "GS", "COP", "TJX", "MDLZ", "LRCX",
    "T", "AMT", "LMT", "MMC", "ADI", "CI", "BA", "CB", "GILD", "VRTX",
    "CVS", "PGR", "SBUX", "REGN", "ZTS", "BSX", "FI", "BDX", "PANW", "ADP",
    "EQIX", "SNPS", "BMY", "CDNS", "MU", "KLAC", "DUK", "SO", "C", "ITW",
    "WM", "SHW", "ATVI", "EOG", "ICE", "MCO", "USB", "APH", "MO", "PYPL",
    "MCK", "MAR", "ORLY", "TT", "SLB", "PH", "ADSK", "ANET", "EMR", "PCAR",
    "NXPI", "ROP", "AON", "MPC", "WELL", "MS", "CTAS", "MNST", "VLO", "ECL",
    "MDT", "CDW", "APD", "D", "NSC", "AJG", "O", "MET", "FTNT", "CPRT",
    "DRE", "TGT", "TRV", "FDX", "NOC", "HUM", "IQV", "AIG", "GPN", "PAYX",
    "ORLY", "PSA", "DLR", "BKR", "VICI", "KDP", "LULU", "WBD", "MCHP", "CMI",
    "OKE", "F", "GM", "EXC", "CNC", "AEP", "GD", "FSLR", "FICO", "CSX",
    "URI", "LEN", "STZ", "IDXX", "PHM", "DXCM", "SNOW", "ON", "MRVL", "TTWO",
    "ENPH", "ALGN", "EPAM", "WDAY", "DDOG", "TEAM", "MDB", "CRWD", "MELI", "SE"
]

EUROPE_TOP_100 = [
    # Tickers format for yfinance: ASML.AS, MC.PA, etc.
    "ASML.AS", "MC.PA", "SAP.DE", "AZN.L", "HSBA.L", "NESN.SW", "ROG.SW", "NOVN.SW", "SHEL.L", "OR.PA",
    "TTE.PA", "SIE.DE", "RMS.PA", "ULVR.L", "NVO", "SAP", "LIN", "DTE.DE", "AIR.PA", "BNP.PA",
    "IBE.MC", "SAN.MC", "BBVA.MC", "ITX.MC", "IFX.DE", "ADS.DE", "BAS.DE", "BAYN.DE", "ALV.DE", "MUV2.DE",
    "BMW.DE", "VOW3.DE", "MBG.DE", "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "STLA.MI", "PRP.PA", "KER.PA",
    "DG.PA", "AI.PA", "BN.PA", "CS.PA", "SAN.PA", "VIV.PA", "GLE.PA", "SU.PA", "DSY.PA", "STMPA.PA",
    "ADYEN.AS", "PRX.AS", "INGA.AS", "KPN.AS", "HEIA.AS", "PHIA.AS", "ABN.AS", "DSM.AS", "AKZA.AS", "NN.AS",
    "ERIC-B.ST", "VOLV-B.ST", "HM-B.ST", "SEB-A.ST", "SHB-A.ST", "SWED-A.ST", "ATCO-A.ST", "SAND.ST", "ASSA-B.ST", "HEXA-B.ST",
    "BP.L", "GSK.L", "RIO.L", "GLEN.L", "AAL.L", "REL.L", "BATS.L", "NG.L", "DGE.L", "VOD.L",
    "ABB.SW", "UBSG.SW", "ZURN.SW", "CSGN.SW", "GIVN.SW", "GEBN.SW", "SRENH.SW", "SCMN.SW", "SLHN.SW", "LONN.SW",
    "CRH", "FLTR.L", "AD.AS", "FER.MC", "REP.MC", "TEF.MC", "GRF.MC", "REE.MC", "AMS.MC", "EL.PA"
]

HK_TOP_100 = [
    "0700.HK", "1398.HK", "1288.HK", "9988.HK", "0005.HK", "0857.HK", "0939.HK", "0941.HK", "3988.HK", "3690.HK",
    "2318.HK", "1211.HK", "9618.HK", "0388.HK", "1810.HK", "2628.HK", "0883.HK", "0001.HK", "0002.HK", "0003.HK",
    "0006.HK", "0011.HK", "0012.HK", "0016.HK", "0017.HK", "0027.HK", "0066.HK", "0101.HK", "0175.HK", "0267.HK",
    "0288.HK", "0291.HK", "0322.HK", "0669.HK", "0688.HK", "0762.HK", "0813.HK", "0823.HK", "0868.HK", "0914.HK",
    "0960.HK", "0968.HK", "0992.HK", "1038.HK", "1044.HK", "1088.HK", "1093.HK", "1109.HK", "1113.HK", "1177.HK",
    "1193.HK", "1299.HK", "1313.HK", "1378.HK", "1876.HK", "1928.HK", "1929.HK", "1997.HK", "2007.HK", "2018.HK",
    "2020.HK", "2269.HK", "2313.HK", "2319.HK", "2331.HK", "2333.HK", "2382.HK", "2388.HK", "2688.HK", "2888.HK",
    "2899.HK", "3323.HK", "3328.HK", "3333.HK", "3618.HK", "3908.HK", "3968.HK", "6030.HK", "6098.HK", "6160.HK",
    "6618.HK", "6690.HK", "6818.HK", "6823.HK", "6862.HK", "6881.HK", "6886.HK", "9888.HK", "9961.HK", "9999.HK",
    "0010.HK", "0019.HK", "0023.HK", "0034.HK", "0083.HK", "0151.HK", "0241.HK", "0270.HK", "0358.HK", "0522.HK"
]

def get_global_universe() -> List[str]:
    """Returns the combined global universe of tickers."""
    return SP500_TOP_200 + EUROPE_TOP_100 + HK_TOP_100
