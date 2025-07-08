from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import Tool, initialize_agent, AgentType
import yfinance as yf
from dotenv import load_dotenv
import math
import re
import datetime
import requests


load_dotenv()


def get_stock_info(query: str) -> str:
    """
    Accepts queries like:
    - "AAPL"
    - "AAPL price"
    - "AAPL price on 2024-07-01"
    - "AAPL close price for last 5 days"
    - "AAPL volume on 2024-06-30"
    - "AAPL high and low for 2024-06-01 to 2024-06-30"
    - "AAPL market cap"
    - "AAPL pe ratio"
    Returns the requested info if available, or a summary if not specific.
    """

    parts = query.strip().split()
    if not parts:
        return "Please provide a ticker symbol."
    ticker = parts[0].upper()
    rest = " ".join(parts[1:]).lower()

    stock = yf.Ticker(ticker)

    # Date or range extraction
    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    dates = re.findall(date_pattern, rest)
    range_pattern = r"(\d{4}-\d{2}-\d{2})\s*(to|-)\s*(\d{4}-\d{2}-\d{2})"
    range_match = re.search(range_pattern, rest)
    last_n_days = re.search(r"last\s+(\d+)\s+days", rest)

    # If a date range is specified
    if range_match:
        start_date, _, end_date = range_match.groups()
        try:
            hist = stock.history(start=start_date, end=end_date)
            if hist.empty:
                return f"No data found for {ticker} from {start_date} to {end_date}."
            summary = []
            for date, row in hist.iterrows():
                summary.append(f"{date.date()}: Open={row['Open']}, High={row['High']}, Low={row['Low']}, Close={row['Close']}, Volume={row['Volume']}")
            return "\n".join(summary)
        except Exception as e:
            return f"Error fetching historical data for {ticker}: {str(e)}"

    # If a single date is specified
    if dates:
        date = dates[0]
        try:
            hist = stock.history(start=date, end=(datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
            if hist.empty:
                return f"No data found for {ticker} on {date}."
            row = hist.iloc[0]
            return f"{ticker} on {date}: Open={row['Open']}, High={row['High']}, Low={row['Low']}, Close={row['Close']}, Volume={row['Volume']}"
        except Exception as e:
            return f"Error fetching data for {ticker} on {date}: {str(e)}"

    # If last N days requested
    if last_n_days:
        n = int(last_n_days.group(1))
        try:
            hist = stock.history(period=f"{n}d")
            if hist.empty:
                return f"No data found for {ticker} for last {n} days."
            summary = []
            for date, row in hist.iterrows():
                summary.append(f"{date.date()}: Open={row['Open']}, High={row['High']}, Low={row['Low']}, Close={row['Close']}, Volume={row['Volume']}")
            return "\n".join(summary)
        except Exception as e:
            return f"Error fetching last {n} days data for {ticker}: {str(e)}"

    # Field-based queries
    field_map = {
        "price": ["regularMarketPrice", "currentPrice"],
        "market cap": ["marketCap"],
        "pe ratio": ["trailingPE", "forwardPE"],
        "open": ["regularMarketOpen"],
        "close": ["regularMarketPreviousClose", "previousClose"],
        "high": ["regularMarketDayHigh", "dayHigh"],
        "low": ["regularMarketDayLow", "dayLow"],
        "volume": ["volume"],
        "dividend yield": ["dividendYield"],
        "dividend": ["dividendRate"],
        "sector": ["sector"],
        "industry": ["industry"],
        "name": ["shortName", "longName"],
        "exchange": ["exchange"],
        "currency": ["currency"],
        "52 week high": ["fiftyTwoWeekHigh"],
        "52 week low": ["fiftyTwoWeekLow"],
    }

    info = None
    try:
        info = stock.info
    except Exception as e:
        return f"Error fetching data for {ticker}: {str(e)}"

    if not info or info is None:
        return f"Could not retrieve data for {ticker}. The service may be rate-limited or unavailable."

    if rest:
        for key, keys in field_map.items():
            if key in rest:
                for k in keys:
                    value = info.get(k)
                    if value is not None:
                        return f"{ticker} {key}: {value}"
                return f"{ticker} {key}: N/A"
        # If field not recognized, return a summary
        return f"{ticker}: {info.get('longName', 'N/A')} | Price: {info.get('regularMarketPrice', 'N/A')} | Market Cap: {info.get('marketCap', 'N/A')}"
    else:
        # If only ticker, return a summary
        return f"{ticker}: {info.get('longName', 'N/A')} | Price: {info.get('regularMarketPrice', 'N/A')} | Market Cap: {info.get('marketCap', 'N/A')}"


yfinance_tool = Tool(
    name="Yahoo Finance (Advanced)",
    func=get_stock_info,
    description=(
        "Get stock price and financial info for a given ticker symbol. "
        "Supports queries like:\n"
        "- 'AAPL' (summary)\n"
        "- 'AAPL price'\n"
        "- 'AAPL price on 2024-07-01'\n"
        "- 'AAPL close price for last 5 days'\n"
        "- 'AAPL volume on 2024-06-30'\n"
        "- 'AAPL high and low for 2024-06-01 to 2024-06-30'\n"
        "- 'AAPL market cap'\n"
        "- 'AAPL pe ratio'\n"
        "Use this tool to answer questions about prices, volume, open/close/high/low, market cap, PE ratio, dividend, sector, industry, and more. "
        "It can also provide historical prices for a specific date or date range, or for the last N days."
    ),
)

def math_tool_func(query: str) -> str:
    """
    Evaluates simple math expressions from a string.
    Supports +, -, *, /, %, **, and parentheses.
    Example: "100 * 1.15", "2500 - 1750", "((5+3)*2)/4"
    """
    try:
        # Only allow safe characters
        allowed = "0123456789+-*/().% "
        if not all(c in allowed for c in query):
            return "Invalid characters in math expression."
        result = eval(query, {"__builtins__": None, "math": math}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating math expression: {str(e)}"


math_tool = Tool(
    name="Math Calculator",
    func=math_tool_func,
    description=(
        "Use this tool to perform simple math calculations, such as addition, subtraction, multiplication, division, "
        "percentage changes, differences, or any other numeric operations needed for financial analysis."
    ),
)


def get_ticker_symbol(company_name: str) -> str:
    """
    Use Yahoo Finance's public search API to find the stock ticker symbol for a given company name.
    Example: "Apple Inc." -> "AAPL"
    """
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        results = response.json()
        if results.get("quotes"):
            return results["quotes"][0].get("symbol", "Ticker not found")
        return "No ticker found"
    except Exception as e:
        return f"Error: {str(e)}"

ticker_lookup_tool = Tool(
    name="Ticker Symbol Finder",
    func=get_ticker_symbol,
    description=(
        "Use this tool to find the stock ticker symbol for a given company name using Yahoo Finance's search API. "
        "For example, to find the ticker for 'Apple Inc.', use this tool and use the result with Yahoo Finance."
    ),
)



# Final-Web search agent
def build_search_agent(llm, verbose=False):
    search = DuckDuckGoSearchResults()
    tools = [
        Tool(name="DuckDuckGo Search", func=search.run, description="Search the web for financial info"),
        ticker_lookup_tool,
        yfinance_tool,
        math_tool,
    ]
    return initialize_agent(
        tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=verbose, handle_parsing_errors=True
    )


