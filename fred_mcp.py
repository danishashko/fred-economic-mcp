#!/usr/bin/env python3
"""
FRED MCP Server

This MCP server provides tools to access U.S. and global economic data from
FRED (Federal Reserve Economic Data, https://fred.stlouisfed.org), including
800,000+ time series: GDP, inflation, unemployment, interest rates, and more.

Requires a free FRED API key (set the FRED_API_KEY environment variable).
Get one instantly at https://fredaccount.stlouisfed.org/apikeys

Built with FastMCP.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from mcp.server.fastmcp import FastMCP

# The MCP stdio transport uses stdout for JSON-RPC only; keep noise off it.
logging.getLogger("fred_mcp").addHandler(logging.NullHandler())

mcp = FastMCP("fred_mcp")

# Constants
FRED_BASE = "https://api.stlouisfed.org/fred/"
CHARACTER_LIMIT = 25000
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3  # FRED allows 120 req/min per key; transient 429s do happen.


# ============================================================================
# ENUMS
# ============================================================================


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class Units(str, Enum):
    """Data value transformations applied by FRED to observations."""

    LEVELS = "lin"  # No transformation
    CHANGE = "chg"
    CHANGE_YOY = "ch1"
    PERCENT_CHANGE = "pch"
    PERCENT_CHANGE_YOY = "pc1"
    COMPOUNDED_ANNUAL_RATE = "pca"
    CONTINUOUSLY_COMPOUNDED = "cch"
    CONTINUOUSLY_COMPOUNDED_ANNUAL = "cca"
    NATURAL_LOG = "log"


class Frequency(str, Enum):
    """Optional lower frequency to aggregate observations to."""

    DEFAULT = ""  # series' native frequency
    DAILY = "d"
    WEEKLY = "w"
    BIWEEKLY = "bw"
    MONTHLY = "m"
    QUARTERLY = "q"
    SEMIANNUAL = "sa"
    ANNUAL = "a"


class SortOrder(str, Enum):
    """Sort order for observation dates."""

    ASC = "asc"
    DESC = "desc"


# A curated set of widely-watched U.S. indicators for the snapshot tool.
SNAPSHOT_SERIES = [
    ("GDPC1", "Real GDP", "Bil. of chained $, SAAR"),
    ("UNRATE", "Unemployment Rate", "%"),
    ("CPIAUCSL", "CPI (All Items)", "Index 1982-84=100"),
    ("PCEPI", "PCE Price Index", "Index 2017=100"),
    ("FEDFUNDS", "Federal Funds Rate", "%"),
    ("DGS10", "10-Year Treasury Yield", "%"),
    ("T10Y2Y", "10Y-2Y Treasury Spread", "%"),
    ("PAYEMS", "Nonfarm Payrolls", "Thousands of persons"),
    ("MORTGAGE30US", "30-Year Mortgage Rate", "%"),
    ("UMCSENT", "Consumer Sentiment (UMich)", "Index 1966=100"),
    ("HOUST", "Housing Starts", "Thousands, SAAR"),
]


# ============================================================================
# API ACCESS
# ============================================================================


class FredError(Exception):
    """Raised for FRED API/transport failures with a clean message."""


def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise FredError("no_api_key")
    return key


def fred_get(path: str, **params: Any) -> Dict[str, Any]:
    """Call a FRED endpoint and return parsed JSON.

    Always requests JSON (the API defaults to XML). Retries transient 429s
    with backoff, since FRED rate-limits at 120 requests/minute per key.
    """
    params["api_key"] = _api_key()
    params["file_type"] = "json"
    # Drop empty/None params so we send clean requests.
    query = {k: v for k, v in params.items() if v is not None and v != ""}
    url = FRED_BASE + path + "?" + urllib.parse.urlencode(query)

    last_err: Optional[str] = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fred-mcp-server"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))  # linear backoff
                last_err = "rate_limit"
                continue
            if e.code == 429:
                raise FredError("rate_limit")
            if e.code == 400:
                # FRED returns a helpful message for bad params/series.
                try:
                    msg = json.loads(body).get("error_message", body)
                except Exception:
                    msg = body
                raise FredError(f"bad_request:{msg[:200]}")
            raise FredError(f"http_{e.code}:{body[:200]}")
        except urllib.error.URLError as e:
            last_err = f"network:{e.reason}"
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise FredError(last_err)
    raise FredError(last_err or "unknown")


def _error_text(what: str, exc: Exception) -> str:
    """Consistent, helpful error message for a failed tool call."""
    msg = str(exc)
    if msg == "no_api_key":
        return (
            "No FRED API key configured.\n\n"
            "Set the `FRED_API_KEY` environment variable to a free key from "
            "https://fredaccount.stlouisfed.org/apikeys and restart the server.\n\n"
            "In Claude Desktop config:\n"
            "```json\n"
            '{\n  "mcpServers": {\n    "fred": {\n      "command": "npx",\n'
            '      "args": ["-y", "fred-mcp-server"],\n'
            '      "env": { "FRED_API_KEY": "your_key_here" }\n    }\n  }\n}\n'
            "```"
        )
    if msg == "rate_limit":
        return (
            f"FRED is rate-limiting requests ({what}).\n\n"
            "FRED allows 120 requests/minute per key. Wait a minute and try again."
        )
    if msg.startswith("bad_request:"):
        return (
            f"FRED rejected the request ({what}): {msg.split(':', 1)[1]}\n\n"
            "Check the series ID or parameters (use search_series to find valid IDs)."
        )
    return (
        f"Error fetching {what}: {msg}\n\n"
        "Check your internet connection and that the series ID is correct."
    )


# ============================================================================
# FORMATTING HELPERS
# ============================================================================


def truncate_response(text: str, message: str = "") -> str:
    if len(text) <= CHARACTER_LIMIT:
        return text
    suffix = (
        f"\n\n⚠️ Response truncated at {CHARACTER_LIMIT} characters. {message}".rstrip()
    )
    # Reserve room for the suffix so the total never exceeds CHARACTER_LIMIT.
    return text[: max(0, CHARACTER_LIMIT - len(suffix))] + suffix


def truncate_json_response(payload: str, message: str = "") -> str:
    if len(payload) <= CHARACTER_LIMIT:
        return payload
    # Don't dump a giant mid-cut preview into context; return a small, valid-JSON
    # message telling the caller to narrow the request. Keeps total output tiny.
    note = (
        f"Response was too large (~{len(payload)} characters) and was not returned in full. "
        f"{message}".strip()
    )
    return json.dumps({"error": "response_too_large", "message": note}, indent=2)


def fmt_value(value: str) -> str:
    """Format a FRED observation value (FRED uses '.' for missing)."""
    if value is None or value == "." or value == "":
        return "N/A"
    try:
        num = float(value)
        return (
            f"{num:,.2f}".rstrip("0").rstrip(".") if "." in value else f"{int(num):,}"
        )
    except (ValueError, TypeError):
        return str(value)


# ============================================================================
# MCP TOOLS
# ============================================================================


@mcp.tool(
    name="search_series",
    annotations={
        "title": "Search FRED Economic Data Series",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def search_series(
    query: Annotated[
        str,
        Field(
            description="Keywords to search for (e.g., 'unemployment rate', 'GDP', 'inflation', 'mortgage rates')",
            min_length=1,
            max_length=200,
        ),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of series to return (1-50)", ge=1, le=50),
    ] = 10,
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """Search for economic data series in FRED by keyword.

    This is the discovery entry point: use it to find the series ID you then
    pass to get_series_observations or get_series_info. Results are ordered by
    popularity so the most relevant series come first.

    Use this tool when:
    - The user names an economic concept but not a specific series ID
    - You need to find what data FRED has on a topic

    Args:
        query: Search keywords.
        limit: Max series to return (1-50).
        response_format: 'markdown' or 'json'.

    Returns:
        str: Matching series with ID, title, units, frequency, and popularity.

    Example:
        Input: {"query": "unemployment rate"}
        Output: UNRATE - Unemployment Rate (%, Monthly) and related series
    """
    try:
        data = fred_get(
            "series/search",
            search_text=query,
            limit=limit,
            order_by="popularity",
            sort_order="desc",
        )
        results = data.get("seriess", [])
        if not results:
            return f"No FRED series found matching '{query}'."

        if response_format == ResponseFormat.MARKDOWN:
            out = f'# FRED Search: "{query}"\n\n'
            out += f"*{data.get('count', len(results)):,} total matches; showing {len(results)}.*\n\n"
            for s in results:
                out += f"## {s.get('id')} — {s.get('title')}\n"
                meta = [
                    s.get("units_short") or s.get("units"),
                    s.get("frequency_short") or s.get("frequency"),
                    s.get("seasonal_adjustment_short"),
                ]
                out += f"*{' · '.join(m for m in meta if m)}*\n"
                out += f"- Range: {s.get('observation_start')} to {s.get('observation_end')}\n"
                out += f"- Popularity: {s.get('popularity')}\n\n"
            return truncate_response(out, "Use a more specific query or lower limit.")
        else:
            items = [
                {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "units": s.get("units"),
                    "frequency": s.get("frequency"),
                    "seasonalAdjustment": s.get("seasonal_adjustment"),
                    "observationStart": s.get("observation_start"),
                    "observationEnd": s.get("observation_end"),
                    "popularity": s.get("popularity"),
                }
                for s in results
            ]
            return truncate_json_response(
                json.dumps(
                    {"query": query, "count": data.get("count"), "results": items},
                    indent=2,
                ),
                "",
            )
    except Exception as e:
        return _error_text("series search", e)


@mcp.tool(
    name="get_series_observations",
    annotations={
        "title": "Get Economic Data Series Values",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_series_observations(
    series_id: Annotated[
        str,
        Field(
            description="FRED series ID (e.g., 'UNRATE', 'GDP', 'CPIAUCSL', 'FEDFUNDS'). Use search_series to find IDs.",
            min_length=1,
            max_length=60,
        ),
    ],
    observation_start: Annotated[
        str,
        Field(
            description="Start date 'YYYY-MM-DD' (optional; default earliest available)"
        ),
    ] = "",
    observation_end: Annotated[
        str,
        Field(description="End date 'YYYY-MM-DD' (optional; default latest available)"),
    ] = "",
    units: Annotated[
        Units,
        Field(
            description="Transformation: 'lin' levels, 'chg' change, 'ch1' change-from-year-ago, 'pch' percent change, 'pc1' percent-change-from-year-ago, 'pca' compounded annual rate, 'log' natural log"
        ),
    ] = Units.LEVELS,
    frequency: Annotated[
        Frequency,
        Field(
            description="Aggregate to a lower frequency: '' native, 'd' daily, 'w' weekly, 'm' monthly, 'q' quarterly, 'a' annual"
        ),
    ] = Frequency.DEFAULT,
    sort_order: Annotated[
        SortOrder,
        Field(description="'asc' oldest-first or 'desc' newest-first"),
    ] = SortOrder.DESC,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of observations to return (1-2000)",
            ge=1,
            le=2000,
        ),
    ] = 50,
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """Get the actual data values (observations) for a FRED economic series.

    This is the core tool. It supports FRED's built-in transformations (percent
    change, year-over-year, etc.) and frequency aggregation (e.g. daily to
    monthly), so you can answer questions like "what's the YoY change in CPI?"
    directly without computing it yourself.

    Use this tool when:
    - The user wants the value(s) of an economic indicator
    - The user wants a trend, a date range, or a transformed view (% change, YoY)

    Args:
        series_id: FRED series ID.
        observation_start / observation_end: optional date range.
        units: transformation (see options).
        frequency: optional aggregation to a lower frequency.
        sort_order: newest- or oldest-first.
        limit: max observations.
        response_format: 'markdown' or 'json'.

    Returns:
        str: The observations, plus the series title and units for context.

    Example:
        Input: {"series_id": "CPIAUCSL", "units": "pc1", "frequency": "m", "limit": 12}
        Output: Year-over-year % change in CPI for the last 12 months
    """
    series_id = series_id.strip().upper()
    try:
        # Fetch the series metadata for human-friendly context (title/units).
        title, native_units = series_id, ""
        try:
            info = fred_get("series", series_id=series_id)
            s0 = (info.get("seriess") or [{}])[0]
            title = s0.get("title", series_id)
            native_units = s0.get("units", "")
        except Exception:
            pass  # observations are the priority; context is best-effort

        data = fred_get(
            "series/observations",
            series_id=series_id,
            observation_start=observation_start or None,
            observation_end=observation_end or None,
            units=units.value,
            frequency=(frequency.value or None),
            sort_order=sort_order.value,
            limit=limit,
        )
        obs = data.get("observations", [])
        if not obs:
            return f"No observations found for '{series_id}' in the requested range."

        unit_label = {
            "lin": native_units or "Levels",
            "chg": "Change",
            "ch1": "Change from year ago",
            "pch": "Percent change",
            "pc1": "Percent change from year ago",
            "pca": "Compounded annual rate of change",
            "cch": "Continuously compounded rate of change",
            "cca": "Continuously compounded annual rate",
            "log": "Natural log",
        }.get(units.value, units.value)

        if response_format == ResponseFormat.MARKDOWN:
            out = f"# {title} ({series_id})\n\n"
            out += f"**Units:** {unit_label}"
            if frequency.value:
                out += f" · **Frequency:** {frequency.value}"
            out += f"\n**Total observations:** {data.get('count', len(obs)):,}\n\n"
            latest = obs[0] if sort_order == SortOrder.DESC else obs[-1]
            out += f"**Latest:** {fmt_value(latest['value'])} ({latest['date']})\n\n"
            out += "| Date | Value |\n|------|------|\n"
            for o in obs:
                out += f"| {o['date']} | {fmt_value(o['value'])} |\n"
            return truncate_response(
                out, "Request a narrower date range or lower limit."
            )
        else:
            payload = {
                "seriesId": series_id,
                "title": title,
                "units": unit_label,
                "frequency": frequency.value or "native",
                "count": data.get("count"),
                "observations": [{"date": o["date"], "value": o["value"]} for o in obs],
            }
            return truncate_json_response(
                json.dumps(payload, indent=2), "Request a narrower range."
            )
    except Exception as e:
        return _error_text(f"observations for {series_id}", e)


@mcp.tool(
    name="get_series_info",
    annotations={
        "title": "Get Economic Series Metadata",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_series_info(
    series_id: Annotated[
        str,
        Field(
            description="FRED series ID (e.g., 'UNRATE', 'GDP'). Use search_series to find IDs.",
            min_length=1,
            max_length=60,
        ),
    ],
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """Get detailed metadata for a FRED series: title, units, frequency, seasonal adjustment, date range, and notes.

    Use this tool when:
    - The user wants to understand what a series measures
    - You need the units/frequency/coverage before pulling observations

    Args:
        series_id: FRED series ID.
        response_format: 'markdown' or 'json'.

    Returns:
        str: The series metadata, including the descriptive notes.

    Example:
        Input: {"series_id": "GDP"}
        Output: Title, units (Billions of Dollars), Quarterly, coverage, notes
    """
    series_id = series_id.strip().upper()
    try:
        data = fred_get("series", series_id=series_id)
        results = data.get("seriess", [])
        if not results:
            return f"No FRED series found with ID '{series_id}'. Use search_series to find valid IDs."
        s = results[0]

        if response_format == ResponseFormat.MARKDOWN:
            out = f"# {s.get('title')} ({s.get('id')})\n\n"
            out += f"- **Units:** {s.get('units')}\n"
            out += f"- **Frequency:** {s.get('frequency')}\n"
            out += f"- **Seasonal Adjustment:** {s.get('seasonal_adjustment')}\n"
            out += f"- **Date Range:** {s.get('observation_start')} to {s.get('observation_end')}\n"
            out += f"- **Last Updated:** {s.get('last_updated')}\n"
            out += f"- **Popularity:** {s.get('popularity')}\n"
            notes = s.get("notes")
            if notes:
                out += f"\n## Notes\n\n{notes}\n"
            return truncate_response(out, "")
        else:
            return truncate_json_response(json.dumps(s, indent=2), "")
    except Exception as e:
        return _error_text(f"series info for {series_id}", e)


@mcp.tool(
    name="get_economic_snapshot",
    annotations={
        "title": "Get U.S. Economic Snapshot",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_economic_snapshot(
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """Get a one-call snapshot of key U.S. economic indicators.

    Pulls the latest value of widely-watched indicators (real GDP, unemployment,
    CPI, PCE, Fed funds rate, 10Y Treasury, the 10Y-2Y spread, nonfarm payrolls,
    30Y mortgage rate, consumer sentiment, housing starts) in a single dashboard.

    Use this tool when:
    - The user asks "how's the economy doing?" or wants a macro overview
    - You want a quick read on current conditions without many separate calls

    Args:
        response_format: 'markdown' or 'json'.

    Returns:
        str: Latest value and date for each headline indicator.

    Example:
        Input: {}
        Output: A dashboard of the latest U.S. macro indicators
    """
    try:
        rows = []
        for sid, label, unit in SNAPSHOT_SERIES:
            try:
                data = fred_get(
                    "series/observations", series_id=sid, sort_order="desc", limit=1
                )
                o = (data.get("observations") or [{}])[0]
                rows.append((sid, label, unit, o.get("value", "."), o.get("date", "")))
            except Exception as e:
                if str(e) == "rate_limit":
                    return _error_text("economic snapshot", e)
                rows.append((sid, label, unit, None, ""))

        if response_format == ResponseFormat.MARKDOWN:
            out = "# U.S. Economic Snapshot\n\n"
            out += "*Latest available value per indicator (FRED).*\n\n"
            out += "| Indicator | Latest | Units | As of |\n|-----------|--------|-------|-------|\n"
            for sid, label, unit, value, date in rows:
                out += f"| {label} (`{sid}`) | {fmt_value(value)} | {unit} | {date or 'N/A'} |\n"
            out += "\n*Use get_series_observations for history or transformations of any indicator.*"
            return truncate_response(out, "")
        else:
            payload = {
                "snapshot": [
                    {
                        "seriesId": sid,
                        "label": label,
                        "units": unit,
                        "value": value,
                        "date": date,
                    }
                    for sid, label, unit, value, date in rows
                ]
            }
            return truncate_json_response(json.dumps(payload, indent=2), "")
    except Exception as e:
        return _error_text("economic snapshot", e)


@mcp.tool(
    name="browse_category",
    annotations={
        "title": "Browse FRED Data Categories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def browse_category(
    category_id: Annotated[
        int,
        Field(
            description="FRED category ID. Use 0 for the top-level root categories.",
            ge=0,
        ),
    ] = 0,
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """Browse FRED's category tree to discover data by topic.

    Start at category 0 (root) to see top-level topics, then pass a child
    category ID to drill in. Shows child categories and the series within the
    category.

    Use this tool when:
    - The user wants to explore what economic data exists by topic
    - You want to navigate from a broad area to specific series

    Args:
        category_id: FRED category ID (0 = root).
        response_format: 'markdown' or 'json'.

    Returns:
        str: The category name, its child categories, and sample series in it.

    Example:
        Input: {"category_id": 0}
        Output: Top-level FRED categories (Money/Banking, National Accounts, ...)
    """
    try:
        children = fred_get("category/children", category_id=category_id).get(
            "categories", []
        )

        # The root (0) has no series of its own; only fetch series for real categories.
        name = "Root"
        series: List[Dict[str, Any]] = []
        if category_id != 0:
            try:
                cat = fred_get("category", category_id=category_id).get(
                    "categories", []
                )
                if cat:
                    name = cat[0].get("name", str(category_id))
            except Exception:
                pass
            try:
                series = fred_get(
                    "category/series",
                    category_id=category_id,
                    limit=10,
                    order_by="popularity",
                    sort_order="desc",
                ).get("seriess", [])
            except Exception:
                series = []

        if not children and not series:
            return f"No subcategories or series found for category {category_id}."

        if response_format == ResponseFormat.MARKDOWN:
            out = f"# FRED Category: {name} (id {category_id})\n\n"
            if children:
                out += "## Subcategories\n\n"
                for c in children:
                    out += f"- **{c.get('name')}** (id `{c.get('id')}`)\n"
                out += "\n"
            if series:
                out += "## Popular Series Here\n\n"
                for s in series:
                    out += f"- `{s.get('id')}` — {s.get('title')} ({s.get('frequency_short')})\n"
            return truncate_response(out, "")
        else:
            payload = {
                "categoryId": category_id,
                "name": name,
                "children": [
                    {"id": c.get("id"), "name": c.get("name")} for c in children
                ],
                "series": [
                    {"id": s.get("id"), "title": s.get("title")} for s in series
                ],
            }
            return truncate_json_response(json.dumps(payload, indent=2), "")
    except Exception as e:
        return _error_text(f"category {category_id}", e)


@mcp.tool(
    name="get_releases",
    annotations={
        "title": "Get Economic Data Releases",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def get_releases(
    limit: Annotated[
        int,
        Field(description="Maximum number of releases to return (1-50)", ge=1, le=50),
    ] = 20,
    response_format: Annotated[
        ResponseFormat,
        Field(
            description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
        ),
    ] = ResponseFormat.MARKDOWN,
) -> str:
    """List economic data releases tracked by FRED (e.g. Employment Situation, CPI, GDP).

    Use this tool when:
    - The user asks about economic data releases or report sources
    - You want to find the official release a series comes from

    Args:
        limit: Max releases to return (1-50).
        response_format: 'markdown' or 'json'.

    Returns:
        str: Releases with name and link.

    Example:
        Input: {"limit": 10}
        Output: A list of major economic data releases
    """
    try:
        data = fred_get(
            "releases", limit=limit, order_by="release_id", sort_order="asc"
        )
        releases = data.get("releases", [])
        if not releases:
            return "No releases found."

        if response_format == ResponseFormat.MARKDOWN:
            out = "# FRED Economic Data Releases\n\n"
            out += f"*{data.get('count', len(releases)):,} total; showing {len(releases)}.*\n\n"
            for r in releases:
                out += f"- **{r.get('name')}** (id `{r.get('id')}`)"
                if r.get("link"):
                    out += f" — [source]({r.get('link')})"
                out += "\n"
            return truncate_response(out, "Raise/lower limit to see more or fewer.")
        else:
            items = [
                {"id": r.get("id"), "name": r.get("name"), "link": r.get("link")}
                for r in releases
            ]
            return truncate_json_response(
                json.dumps({"count": data.get("count"), "releases": items}, indent=2),
                "",
            )
    except Exception as e:
        return _error_text("releases", e)


# ============================================================================
# RUN SERVER
# ============================================================================


def main() -> None:
    """Run the MCP server with stdio transport (default for Claude Desktop)."""
    mcp.run()


if __name__ == "__main__":
    main()
