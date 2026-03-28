"""
NSE Stock Universe — Nifty 50, Nifty 100, Nifty 200 constituent symbols.
Updated periodically. Symbols are in yfinance format (without .NS suffix).
"""

NIFTY_50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL",
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK",
    "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]

NIFTY_100 = NIFTY_50 + [
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "ATGL",
    "BANKBARODA", "BERGEPAINT", "BOSCHLTD", "CANBK", "CHOLAFIN",
    "COLPAL", "DLF", "DABUR", "DIVISLAB", "GAIL",
    "GODREJCP", "HAVELLS", "ICICIPRULI", "ICICIGI", "INDIGO",
    "IOC", "IRCTC", "JIOFIN", "JINDALSTEL", "LICI",
    "LUPIN", "MARICO", "MOTHERSON", "NAUKRI", "NHPC",
    "PIDILITIND", "PNB", "RECLTD", "SBICARD", "SHREECEM",
    "SHRIRAMFIN", "SIEMENS", "SRF", "TATAPOWER", "TORNTPHARM",
    "TVSMOTOR", "UNIONBANK", "UNITDSPR", "VEDL", "VBL",
    "VOLTAS", "ZOMATO", "ZYDUSLIFE", "HAL", "PFC",
]

NIFTY_200 = NIFTY_100 + [
    "AUROPHARMA", "BAJAJHLDNG", "BANDHANBNK", "BATAINDIA", "BHEL",
    "BIOCON", "CANFINHOME", "CONCOR", "CROMPTON", "CUMMINSIND",
    "DEEPAKNTR", "ESCORTS", "EXIDEIND", "FEDERALBNK", "FORTIS",
    "GLENMARK", "GMRINFRA", "GODREJPROP", "GSPL", "HINDPETRO",
    "IDFCFIRSTB", "INDUSTOWER", "IRFC", "JKCEMENT", "JSL",
    "JUBLFOOD", "KPITTECH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN",
    "LTIM", "LTTS", "MANAPPURAM", "MAXHEALTH", "MFSL",
    "MPHASIS", "MRF", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM",
    "NAVINFLUOR", "OBEROIRLTY", "OFSS", "PAGEIND", "PATANJALI",
    "PERSISTENT", "PETRONET", "POLYCAB", "PRESTIGE", "PVRINOX",
    "RAMCOCEM", "SAIL", "SCHAEFFLER", "SONACOMS", "STARHEALTH",
    "SUNDARMFIN", "SUPREMEIND", "SYNGENE", "TATACHEM", "TATACOMM",
    "TATAELXSI", "THERMAX", "TIINDIA", "TORNTPOWER", "TRIDENT",
    "UCOBANK", "UPL", "WHIRLPOOL", "YESBANK", "ZEEL",
]

# Sector classification for Nifty 50
SECTOR_MAP = {
    "ADANIENT": "Conglomerate", "ADANIPORTS": "Infrastructure",
    "APOLLOHOSP": "Healthcare", "ASIANPAINT": "Consumer",
    "AXISBANK": "Banking", "BAJAJ-AUTO": "Auto",
    "BAJFINANCE": "Finance", "BAJAJFINSV": "Finance",
    "BEL": "Defence", "BPCL": "Oil & Gas",
    "BHARTIARTL": "Telecom", "BRITANNIA": "FMCG",
    "CIPLA": "Pharma", "COALINDIA": "Mining",
    "DRREDDY": "Pharma", "EICHERMOT": "Auto",
    "ETERNAL": "Internet", "GRASIM": "Cement",
    "HCLTECH": "IT", "HDFCBANK": "Banking",
    "HDFCLIFE": "Insurance", "HEROMOTOCO": "Auto",
    "HINDALCO": "Metals", "HINDUNILVR": "FMCG",
    "ICICIBANK": "Banking", "ITC": "FMCG",
    "INDUSINDBK": "Banking", "INFY": "IT",
    "JSWSTEEL": "Metals", "KOTAKBANK": "Banking",
    "LT": "Infrastructure", "M&M": "Auto",
    "MARUTI": "Auto", "NTPC": "Power",
    "NESTLEIND": "FMCG", "ONGC": "Oil & Gas",
    "POWERGRID": "Power", "RELIANCE": "Conglomerate",
    "SBILIFE": "Insurance", "SBIN": "Banking",
    "SUNPHARMA": "Pharma", "TCS": "IT",
    "TATACONSUM": "FMCG", "TATAMOTORS": "Auto",
    "TATASTEEL": "Metals", "TECHM": "IT",
    "TITAN": "Consumer", "TRENT": "Retail",
    "ULTRACEMCO": "Cement", "WIPRO": "IT",
}
