"""Seed the database with sample data for US Stocks AI."""
import database as db

# Sample data with S&P 500 Top 50 stocks
SAMPLE_DATA = {
    "date": "2025-01-30",
    "analysis": {
        "AAPL": {"symbol": "AAPL", "company_name": "Apple Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "MSFT": {"symbol": "MSFT", "company_name": "Microsoft Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "NVDA": {"symbol": "NVDA", "company_name": "NVIDIA Corporation", "decision": "BUY", "confidence": "HIGH", "risk": "MEDIUM"},
        "AMZN": {"symbol": "AMZN", "company_name": "Amazon.com, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "GOOGL": {"symbol": "GOOGL", "company_name": "Alphabet Inc.", "decision": "BUY", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "META": {"symbol": "META", "company_name": "Meta Platforms, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "BRK-B": {"symbol": "BRK-B", "company_name": "Berkshire Hathaway Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "AVGO": {"symbol": "AVGO", "company_name": "Broadcom Inc.", "decision": "BUY", "confidence": "HIGH", "risk": "MEDIUM"},
        "LLY": {"symbol": "LLY", "company_name": "Eli Lilly and Company", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "JPM": {"symbol": "JPM", "company_name": "JPMorgan Chase & Co.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "TSLA": {"symbol": "TSLA", "company_name": "Tesla, Inc.", "decision": "SELL", "confidence": "MEDIUM", "risk": "HIGH"},
        "XOM": {"symbol": "XOM", "company_name": "Exxon Mobil Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "UNH": {"symbol": "UNH", "company_name": "UnitedHealth Group Incorporated", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "V": {"symbol": "V", "company_name": "Visa Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "MA": {"symbol": "MA", "company_name": "Mastercard Incorporated", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "PG": {"symbol": "PG", "company_name": "The Procter & Gamble Company", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "COST": {"symbol": "COST", "company_name": "Costco Wholesale Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "JNJ": {"symbol": "JNJ", "company_name": "Johnson & Johnson", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "HD": {"symbol": "HD", "company_name": "The Home Depot, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "ABBV": {"symbol": "ABBV", "company_name": "AbbVie Inc.", "decision": "BUY", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "WMT": {"symbol": "WMT", "company_name": "Walmart Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "NFLX": {"symbol": "NFLX", "company_name": "Netflix, Inc.", "decision": "BUY", "confidence": "HIGH", "risk": "MEDIUM"},
        "CRM": {"symbol": "CRM", "company_name": "Salesforce, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "BAC": {"symbol": "BAC", "company_name": "Bank of America Corporation", "decision": "SELL", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "ORCL": {"symbol": "ORCL", "company_name": "Oracle Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "CVX": {"symbol": "CVX", "company_name": "Chevron Corporation", "decision": "SELL", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "MRK": {"symbol": "MRK", "company_name": "Merck & Co., Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "KO": {"symbol": "KO", "company_name": "The Coca-Cola Company", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "AMD": {"symbol": "AMD", "company_name": "Advanced Micro Devices, Inc.", "decision": "BUY", "confidence": "MEDIUM", "risk": "HIGH"},
        "CSCO": {"symbol": "CSCO", "company_name": "Cisco Systems, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "PEP": {"symbol": "PEP", "company_name": "PepsiCo, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "ACN": {"symbol": "ACN", "company_name": "Accenture plc", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "TMO": {"symbol": "TMO", "company_name": "Thermo Fisher Scientific Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "LIN": {"symbol": "LIN", "company_name": "Linde plc", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "ADBE": {"symbol": "ADBE", "company_name": "Adobe Inc.", "decision": "SELL", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "MCD": {"symbol": "MCD", "company_name": "McDonald's Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "ABT": {"symbol": "ABT", "company_name": "Abbott Laboratories", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "WFC": {"symbol": "WFC", "company_name": "Wells Fargo & Company", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "GE": {"symbol": "GE", "company_name": "GE Aerospace", "decision": "BUY", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "IBM": {"symbol": "IBM", "company_name": "International Business Machines Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "DHR": {"symbol": "DHR", "company_name": "Danaher Corporation", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "QCOM": {"symbol": "QCOM", "company_name": "QUALCOMM Incorporated", "decision": "SELL", "confidence": "MEDIUM", "risk": "HIGH"},
        "CAT": {"symbol": "CAT", "company_name": "Caterpillar Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "INTU": {"symbol": "INTU", "company_name": "Intuit Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "DIS": {"symbol": "DIS", "company_name": "The Walt Disney Company", "decision": "SELL", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "AMAT": {"symbol": "AMAT", "company_name": "Applied Materials, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "TXN": {"symbol": "TXN", "company_name": "Texas Instruments Incorporated", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "NOW": {"symbol": "NOW", "company_name": "ServiceNow, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
        "PM": {"symbol": "PM", "company_name": "Philip Morris International Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "LOW"},
        "GS": {"symbol": "GS", "company_name": "The Goldman Sachs Group, Inc.", "decision": "HOLD", "confidence": "MEDIUM", "risk": "MEDIUM"},
    },
    "summary": {
        "total": 50,
        "buy": 7,
        "sell": 6,
        "hold": 37,
    },
    "top_picks": [
        {
            "rank": 1,
            "symbol": "NVDA",
            "company_name": "NVIDIA Corporation",
            "decision": "BUY",
            "reason": "Strong AI demand driving record revenue growth, dominant market position in data center GPUs.",
            "risk_level": "MEDIUM",
        },
        {
            "rank": 2,
            "symbol": "AVGO",
            "company_name": "Broadcom Inc.",
            "decision": "BUY",
            "reason": "AI networking and custom chip demand accelerating, VMware integration boosting margins.",
            "risk_level": "MEDIUM",
        },
        {
            "rank": 3,
            "symbol": "NFLX",
            "company_name": "Netflix, Inc.",
            "decision": "BUY",
            "reason": "Subscriber growth re-accelerating, ad-tier monetization improving, strong content pipeline.",
            "risk_level": "MEDIUM",
        },
    ],
    "stocks_to_avoid": [
        {
            "symbol": "TSLA",
            "company_name": "Tesla, Inc.",
            "reason": "Margin compression from price cuts, increasing competition in EV market. High volatility.",
        },
        {
            "symbol": "QCOM",
            "company_name": "QUALCOMM Incorporated",
            "reason": "Smartphone market weakness, Apple modem transition risk. Elevated risk profile.",
        },
        {
            "symbol": "DIS",
            "company_name": "The Walt Disney Company",
            "reason": "Streaming profitability challenges, declining linear TV revenue. Ongoing restructuring.",
        },
        {
            "symbol": "ADBE",
            "company_name": "Adobe Inc.",
            "reason": "AI competition concerns weighing on valuation, slowing creative cloud growth.",
        },
    ],
}


def seed_database():
    """Seed the database with sample data."""
    print("Seeding database...")

    db.save_recommendation(
        date=SAMPLE_DATA["date"],
        analysis_data=SAMPLE_DATA["analysis"],
        summary=SAMPLE_DATA["summary"],
        top_picks=SAMPLE_DATA["top_picks"],
        stocks_to_avoid=SAMPLE_DATA["stocks_to_avoid"],
    )

    print(f"Saved recommendation for {SAMPLE_DATA['date']}")
    print(f"  - {len(SAMPLE_DATA['analysis'])} stocks analyzed")
    print(f"  - Summary: {SAMPLE_DATA['summary']['buy']} BUY, {SAMPLE_DATA['summary']['sell']} SELL, {SAMPLE_DATA['summary']['hold']} HOLD")
    print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()
