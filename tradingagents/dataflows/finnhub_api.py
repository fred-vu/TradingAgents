"""Finnhub API integrations for real-time fundamentals and news."""

from __future__ import annotations

import os
from datetime import datetime
from typing import List

try:
    import finnhub  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    finnhub = None


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY") or ""
_client = None
IS_AVAILABLE = bool(finnhub and FINNHUB_API_KEY)


def _require_client():
    if not finnhub:
        raise RuntimeError(
            "finnhub-python is not installed. Install it or remove Finnhub from vendor priority."
        )
    if not FINNHUB_API_KEY:
        raise RuntimeError(
            "FINNHUB_API_KEY is not set. Export it before using Finnhub vendors."
        )
    global _client
    if _client is None:
        _client = finnhub.Client(api_key=FINNHUB_API_KEY)
    return _client


def _format_news(articles: List[dict], header: str) -> str:
    if not articles:
        return f"{header}\nNo recent articles found."

    formatted = [header]
    for article in articles:
        published = article.get("datetime")
        if isinstance(published, (int, float)):
            published = datetime.utcfromtimestamp(published).strftime("%Y-%m-%d %H:%M")
        formatted.append(
            f"- **{article.get('headline', 'Untitled')}** ({published})\n  {article.get('summary', '')}\n  Source: {article.get('source', 'Unknown')}"
        )
    return "\n".join(formatted)


def get_finnhub_company_news(
    symbol: str,
    start_date: str,
    end_date: str,
) -> str:
    """Fetch company-specific news via Finnhub."""

    client = _require_client()
    articles = client.company_news(symbol.upper(), _from=start_date, to=end_date)
    header = f"## Finnhub Company News for {symbol.upper()} ({start_date} → {end_date})"
    return _format_news(articles[:10], header)


def _format_financial_section(title: str, rows: List[str]) -> str:
    if not rows:
        return f"### {title}\nNo data available\n"
    return f"### {title}\n" + "\n".join(rows) + "\n"


def get_finnhub_basic_financials(ticker: str, curr_date: str) -> str:
    """Return key metrics using Finnhub basic financials endpoint."""

    client = _require_client()
    data = client.company_basic_financials(ticker.upper(), metric="all")
    metric = data.get("metric", {})

    rows = [
        f"- Market Cap: {metric.get('marketCapitalization', 'N/A')} USD",
        f"- P/E (TTM): {metric.get('peNormalizedAnnual', 'N/A')}",
        f"- Revenue (TTM): {metric.get('revenueTTM', 'N/A')} USD",
        f"- Net Margin (TTM): {metric.get('netMarginTTM', 'N/A')}",
        f"- Debt/Equity: {metric.get('totalDebt/totalEquity', 'N/A')}",
    ]

    return _format_financial_section(
        f"Finnhub Basic Financials for {ticker.upper()} (as of {curr_date})",
        rows,
    )


def _latest_report(records: List[dict], statement_name: str) -> str:
    if not records:
        return f"No {statement_name} data available."
    latest = records[0]
    rows = [
        f"Period: {latest.get('period')} | Calendar Date: {latest.get('calendarDate')}",
        f"Fiscal Year: {latest.get('fiscalYear', 'N/A')} Quarter: {latest.get('fiscalQuarter', 'N/A')}"
    ]
    line_items = latest.get("items", [])
    for item in line_items[:15]:  # limit to avoid overly long output
        rows.append(f"- {item.get('label')}: {item.get('value', 'N/A')}")
    return "\n".join(rows)


def _get_financials_reported(ticker: str, section: str) -> List[dict]:
    client = _require_client()
    response = client.financials_reported(symbol=ticker.upper(), freq="quarterly")
    reports = response.get("data", [])
    formatted: List[dict] = []
    for report in reports:
        line_items = report.get("report", {}).get(section, [])
        if not line_items:
            continue
        formatted.append(
            {
                "period": report.get("period"),
                "calendarDate": report.get("calendarDate"),
                "fiscalYear": report.get("fiscalYear"),
                "fiscalQuarter": report.get("fiscalQuarter"),
                "items": line_items,
            }
        )
    return formatted


def get_finnhub_income_statement(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    reports = _get_financials_reported(ticker, section="ic")
    header = f"## Finnhub Income Statement Snapshot ({ticker.upper()})"
    return f"{header}\n{_latest_report(reports, 'income statement')}"


def get_finnhub_balance_sheet(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    reports = _get_financials_reported(ticker, section="bs")
    header = f"## Finnhub Balance Sheet Snapshot ({ticker.upper()})"
    return f"{header}\n{_latest_report(reports, 'balance sheet')}"


def get_finnhub_cashflow(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    reports = _get_financials_reported(ticker, section="cf")
    header = f"## Finnhub Cashflow Statement Snapshot ({ticker.upper()})"
    return f"{header}\n{_latest_report(reports, 'cashflow statement')}"
