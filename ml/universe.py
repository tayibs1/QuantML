"""
Trading universe plus static metadata (company name, sector).

A hand-picked, liquid slice of the NASDAQ-100. Cross-sectional features need a
decent breadth of names to be meaningful, so I keep it around 55. Add or swap
names freely; everything downstream just reads UNIVERSE.
"""
from __future__ import annotations

# ticker -> (company, sector)
TICKERS: dict[str, tuple[str, str]] = {
    "AAPL": ("Apple", "Technology"),
    "MSFT": ("Microsoft", "Technology"),
    "NVDA": ("NVIDIA", "Technology"),
    "AMZN": ("Amazon", "Consumer Discretionary"),
    "GOOGL": ("Alphabet", "Communication Services"),
    "META": ("Meta Platforms", "Communication Services"),
    "TSLA": ("Tesla", "Consumer Discretionary"),
    "AMD": ("Advanced Micro Devices", "Technology"),
    "AVGO": ("Broadcom", "Technology"),
    "ADBE": ("Adobe", "Technology"),
    "COST": ("Costco", "Consumer Staples"),
    "PEP": ("PepsiCo", "Consumer Staples"),
    "NFLX": ("Netflix", "Communication Services"),
    "CSCO": ("Cisco", "Technology"),
    "TMUS": ("T-Mobile US", "Communication Services"),
    "INTC": ("Intel", "Technology"),
    "QCOM": ("Qualcomm", "Technology"),
    "TXN": ("Texas Instruments", "Technology"),
    "AMAT": ("Applied Materials", "Technology"),
    "INTU": ("Intuit", "Technology"),
    "AMGN": ("Amgen", "Health Care"),
    "ISRG": ("Intuitive Surgical", "Health Care"),
    "BKNG": ("Booking Holdings", "Consumer Discretionary"),
    "HON": ("Honeywell", "Industrials"),
    "VRTX": ("Vertex Pharmaceuticals", "Health Care"),
    "ADI": ("Analog Devices", "Technology"),
    "REGN": ("Regeneron", "Health Care"),
    "GILD": ("Gilead Sciences", "Health Care"),
    "LRCX": ("Lam Research", "Technology"),
    "MU": ("Micron Technology", "Technology"),
    "PANW": ("Palo Alto Networks", "Technology"),
    "MELI": ("MercadoLibre", "Consumer Discretionary"),
    "SBUX": ("Starbucks", "Consumer Discretionary"),
    "MDLZ": ("Mondelez", "Consumer Staples"),
    "ADP": ("Automatic Data Processing", "Industrials"),
    "KLAC": ("KLA Corporation", "Technology"),
    "SNPS": ("Synopsys", "Technology"),
    "CDNS": ("Cadence Design Systems", "Technology"),
    "MAR": ("Marriott International", "Consumer Discretionary"),
    "ORLY": ("O'Reilly Automotive", "Consumer Discretionary"),
    "CSX": ("CSX Corporation", "Industrials"),
    "ASML": ("ASML Holding", "Technology"),
    "CRWD": ("CrowdStrike", "Technology"),
    "FTNT": ("Fortinet", "Technology"),
    "ABNB": ("Airbnb", "Consumer Discretionary"),
    "PYPL": ("PayPal", "Financials"),
    "NXPI": ("NXP Semiconductors", "Technology"),
    "PCAR": ("PACCAR", "Industrials"),
    "MNST": ("Monster Beverage", "Consumer Staples"),
    "ROST": ("Ross Stores", "Consumer Discretionary"),
    "ODFL": ("Old Dominion Freight Line", "Industrials"),
    "DXCM": ("DexCom", "Health Care"),
    "IDXX": ("IDEXX Laboratories", "Health Care"),
    "FAST": ("Fastenal", "Industrials"),
    "CTAS": ("Cintas", "Industrials"),
    "WDAY": ("Workday", "Technology"),
}

UNIVERSE: list[str] = list(TICKERS.keys())

# Benchmark for the equity curve (downloaded, not part of cross-sectional features).
BENCHMARK = "QQQ"


def company(ticker: str) -> str:
    return TICKERS.get(ticker, (ticker, "—"))[0]


def sector(ticker: str) -> str:
    return TICKERS.get(ticker, (ticker, "—"))[1]
