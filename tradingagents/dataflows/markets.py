"""
Market configuration and stock lists.
Supports US market (S&P 500 Top 50 stocks).
"""

from enum import Enum
from typing import Optional


class Market(Enum):
    """Supported markets."""
    US = "us"


# S&P 500 Top 50 stocks by market cap with company names
SP500_TOP_50_STOCKS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "BRK-B": "Berkshire Hathaway Inc.",
    "AVGO": "Broadcom Inc.",
    "LLY": "Eli Lilly and Company",
    "JPM": "JPMorgan Chase & Co.",
    "TSLA": "Tesla, Inc.",
    "XOM": "Exxon Mobil Corporation",
    "UNH": "UnitedHealth Group Incorporated",
    "V": "Visa Inc.",
    "MA": "Mastercard Incorporated",
    "PG": "The Procter & Gamble Company",
    "COST": "Costco Wholesale Corporation",
    "JNJ": "Johnson & Johnson",
    "HD": "The Home Depot, Inc.",
    "ABBV": "AbbVie Inc.",
    "WMT": "Walmart Inc.",
    "NFLX": "Netflix, Inc.",
    "CRM": "Salesforce, Inc.",
    "BAC": "Bank of America Corporation",
    "ORCL": "Oracle Corporation",
    "CVX": "Chevron Corporation",
    "MRK": "Merck & Co., Inc.",
    "KO": "The Coca-Cola Company",
    "AMD": "Advanced Micro Devices, Inc.",
    "CSCO": "Cisco Systems, Inc.",
    "PEP": "PepsiCo, Inc.",
    "ACN": "Accenture plc",
    "TMO": "Thermo Fisher Scientific Inc.",
    "LIN": "Linde plc",
    "ADBE": "Adobe Inc.",
    "MCD": "McDonald's Corporation",
    "ABT": "Abbott Laboratories",
    "WFC": "Wells Fargo & Company",
    "GE": "GE Aerospace",
    "IBM": "International Business Machines Corporation",
    "DHR": "Danaher Corporation",
    "QCOM": "QUALCOMM Incorporated",
    "CAT": "Caterpillar Inc.",
    "INTU": "Intuit Inc.",
    "DIS": "The Walt Disney Company",
    "AMAT": "Applied Materials, Inc.",
    "TXN": "Texas Instruments Incorporated",
    "NOW": "ServiceNow, Inc.",
    "PM": "Philip Morris International Inc.",
    "GS": "The Goldman Sachs Group, Inc.",
}


def is_sp500_top50_stock(symbol: str) -> bool:
    """
    Check if a symbol is an S&P 500 Top 50 stock.

    Args:
        symbol: Stock symbol

    Returns:
        True if the symbol is in the S&P 500 Top 50 list
    """
    clean_symbol = symbol.upper()
    return clean_symbol in SP500_TOP_50_STOCKS


def get_sp500_top50_company_name(symbol: str) -> Optional[str]:
    """
    Get the company name for an S&P 500 Top 50 stock symbol.

    Args:
        symbol: Stock symbol

    Returns:
        Company name if found, None otherwise
    """
    clean_symbol = symbol.upper()
    return SP500_TOP_50_STOCKS.get(clean_symbol)


def detect_market(symbol: str, config_market: str = "auto") -> Market:
    """
    Detect the market for a given symbol.

    Args:
        symbol: Stock symbol
        config_market: Market setting from config ("auto", "us")

    Returns:
        Market enum indicating the detected market
    """
    return Market.US


def normalize_symbol(symbol: str, target: str = "yfinance") -> str:
    """
    Normalize a symbol for a specific data source.

    Args:
        symbol: Stock symbol
        target: Target format ("yfinance")

    Returns:
        Normalized symbol for the target
    """
    return symbol.upper()


def get_sp500_top50_list() -> list:
    """
    Get list of all S&P 500 Top 50 stock symbols.

    Returns:
        List of S&P 500 Top 50 stock symbols
    """
    return list(SP500_TOP_50_STOCKS.keys())


def get_sp500_top50_with_names() -> dict:
    """
    Get dictionary of S&P 500 Top 50 stocks with company names.

    Returns:
        Dictionary mapping symbols to company names
    """
    return SP500_TOP_50_STOCKS.copy()
