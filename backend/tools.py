"""LangChain tool integrations with flag-based enablement.

Implements a small set of always-free tools plus optional paid search (Tavily).
Use `get_available_tools()` to fetch the enabled tools list based on environment flags.
"""

from __future__ import annotations

import os
from typing import List

# Tool import: prefer langchain_core, fall back to langchain.tools for older installs
try:
    from langchain_core.tools import Tool  # type: ignore
except ImportError:  # pragma: no cover
    from langchain.tools import Tool  # type: ignore

from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun, ArxivQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import yfinance as yf

# Optional: Python REPL from langchain_experimental; fall back to a simple evaluator
try:
    from langchain_experimental.tools import PythonREPLTool  # type: ignore
except ImportError:  # pragma: no cover
    PythonREPLTool = None

# Optional: Tavily (paid, flag + key)
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except Exception:  # pragma: no cover
    TavilySearchResults = None


def calculator_tool() -> Tool:
    """Calculator/REPL tool (always available, no API key)."""
    if PythonREPLTool is not None:
        repl = PythonREPLTool()
        return Tool(
            name="calculator",
            func=repl.run,
            description="Execute Python code for calculations or quick logic (e.g., '2+2', 'sum([1,2,3])').",
        )

    # Fallback: minimal evaluator using math only
    import math

    def _safe_eval(expr: str) -> str:
        try:
            allowed_globals = {"__builtins__": {}}
            allowed_locals = {"math": math}
            result = eval(expr, allowed_globals, allowed_locals)
            return str(result)
        except Exception as exc:  # pragma: no cover
            return f"Error: {exc}"

    return Tool(
        name="calculator",
        func=_safe_eval,
        description="Basic calculator (math.* available) when PythonREPLTool is unavailable.",
    )


def wikipedia_tool() -> Tool:
    """Wikipedia lookup (free)."""
    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    return Tool(
        name="wikipedia",
        func=wikipedia.run,
        description="Search Wikipedia for factual information (e.g., 'Tell me about Python programming').",
    )


def arxiv_tool() -> Tool:
    """ArXiv search (free)."""
    arxiv = ArxivQueryRun()
    return Tool(
        name="arxiv",
        func=arxiv.run,
        description="Search ArXiv for research papers (e.g., 'papers about large language models').",
    )


def duckduckgo_tool() -> Tool:
    """DuckDuckGo web search (free)."""
    try:
        search = DuckDuckGoSearchRun()
        return Tool(
            name="web_search",
            func=search.run,
            description="General web search for news/current info (e.g., 'latest AI news').",
        )
    except ImportError:
        return None


def yahoo_finance_tool() -> Tool:
    """Yahoo Finance stock data (free)."""

    def get_stock_price(ticker: str) -> str:
        symbol = (ticker or "").strip().split()[0].upper()
        if not symbol:
            return "Error: missing ticker symbol"

        try:
            stock = yf.Ticker(ticker)
            price = None
            market_cap = None

            # Prefer fast_info when available
            fast_info = getattr(stock, "fast_info", None)
            if fast_info:
                price = getattr(fast_info, "last_price", None)
                market_cap = getattr(fast_info, "market_cap", None)

            if price is None:
                info = stock.info
                price = info.get("currentPrice")
                market_cap = info.get("marketCap")

            # Format price if present
            if isinstance(price, (int, float)):
                price_str = f"${price:,.2f}"
            else:
                price_str = "N/A"

            return f"{symbol}: {price_str}"
        except Exception as exc:  # pragma: no cover
            return f"Error fetching {ticker}: {exc}"

    return Tool(
        name="stock_data",
        func=get_stock_price,
        description="Get stock price/market cap via Yahoo Finance (e.g., 'AAPL').",
    )


def tavily_tool(api_key: str) -> Tool:
    """Tavily search (paid, requires key + flag)."""
    if TavilySearchResults is None:
        raise RuntimeError("Tavily not installed; ensure langchain_community is available.")

    search = TavilySearchResults(
        api_key=api_key,
        max_results=3,
        search_depth="advanced",
        include_answer=True,
    )
    return Tool(
        name="tavily_search",
        func=search.invoke,
        description="Advanced web search (paid) for richer current-event answers.",
    )


def get_available_tools() -> List[Tool]:
    """Return enabled tools based on environment flags."""
    tools: List[Tool] = [
        calculator_tool(),
        wikipedia_tool(),
        arxiv_tool(),
        duckduckgo_tool(),
        yahoo_finance_tool(),
    ]

    # Drop any None entries (e.g., missing ddgs dependency)
    tools = [t for t in tools if t is not None]

    enable_tavily = os.getenv("ENABLE_TAVILY", "false").lower() == "true"
    api_key = os.getenv("TAVILY_API_KEY")

    if enable_tavily and api_key:
        try:
            tools.append(tavily_tool(api_key))
        except Exception:
            # Fail silently here; downstream can log if desired
            pass

    return tools
