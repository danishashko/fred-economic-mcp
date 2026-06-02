# FRED MCP Server 📊

[![npm version](https://img.shields.io/npm/v/fred-economic-mcp.svg)](https://www.npmjs.com/package/fred-economic-mcp)
[![npm downloads](https://img.shields.io/npm/dm/fred-economic-mcp.svg)](https://www.npmjs.com/package/fred-economic-mcp)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

U.S. and global economic data for Claude Desktop and any MCP-compatible client, powered by [FRED](https://fred.stlouisfed.org) (Federal Reserve Economic Data). Search and pull from **800,000+ economic time series** — GDP, inflation, unemployment, interest rates, and more — all from natural language.

> **npm package:** [`fred-economic-mcp`](https://www.npmjs.com/package/fred-economic-mcp) &nbsp;·&nbsp; **GitHub repo:** [`danishashko/fred-economic-mcp`](https://github.com/danishashko/fred-economic-mcp).

## 🎯 What You Get

- 🔎 **Search** 800k+ economic series by keyword
- 📈 **Observations** with built-in transforms (levels, % change, year-over-year) and frequency aggregation (daily → monthly/quarterly/annual)
- 🧾 **Series metadata** — units, frequency, seasonal adjustment, coverage, notes
- 🇺🇸 **Economic snapshot** — key U.S. indicators in one call
- 🗂️ **Category browsing** to discover data by topic
- 🗓️ **Releases** tracked by FRED

Every tool returns human-readable **markdown** by default, or structured **JSON** on request (`response_format: "json"`). The server is lightweight (Python standard library + `mcp` only), applies FRED's transformations server-side so the AI gets clean numbers, and retries automatically when FRED rate-limits.

## 🔑 Get a Free API Key (required)

FRED requires a free API key. It takes about a minute:

1. Create an account at [fredaccount.stlouisfed.org](https://fredaccount.stlouisfed.org/login/secure/) and request a key at [fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys).
2. Provide it to the server via the `FRED_API_KEY` environment variable (see config below).

## 🚀 Quick Start

Add this to your Claude Desktop config and restart Claude:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fred": {
      "command": "npx",
      "args": ["-y", "fred-economic-mcp"],
      "env": {
        "FRED_API_KEY": "your_free_fred_api_key_here"
      }
    }
  }
}
```

On first launch the npx wrapper creates an isolated Python environment and installs the dependencies for you (a one-time step that can take a minute). You only need **Python 3.10+** and **Node.js 16+** on your machine.

### Prefer a global install?

```bash
npm install -g fred-economic-mcp
```

```json
{
  "mcpServers": {
    "fred": {
      "command": "fred-economic-mcp",
      "env": { "FRED_API_KEY": "your_free_fred_api_key_here" }
    }
  }
}
```

## 🔧 Available Tools

| Tool | What it returns | Parameters |
|------|-----------------|------------|
| `search_series` | Series matching a keyword, ranked by popularity (ID, title, units, frequency) | `query`, `limit` |
| `get_series_observations` | The actual data values, with transforms and frequency aggregation | `series_id`, `observation_start`, `observation_end`, `units`, `frequency`, `sort_order`, `limit` |
| `get_series_info` | Metadata for a series (units, frequency, seasonal adjustment, coverage, notes) | `series_id` |
| `get_economic_snapshot` | Latest value of key U.S. indicators in one dashboard | *(none)* |
| `browse_category` | Child categories and popular series within a FRED category | `category_id` |
| `get_releases` | Economic data releases FRED tracks | `limit` |

Every tool also accepts `response_format` (`"markdown"`, the default, or `"json"`).

**`get_series_observations` transforms (`units`):** `lin` levels · `chg` change · `ch1` change from year ago · `pch` percent change · `pc1` percent change from year ago · `pca` compounded annual rate · `log` natural log.

**Frequency aggregation (`frequency`):** empty (native) · `d` daily · `w` weekly · `m` monthly · `q` quarterly · `a` annual.

### Popular series IDs

You don't need to memorize IDs — `search_series` finds them — but these come up often:

| Series ID | Indicator |
|-----------|-----------|
| `GDPC1` | Real Gross Domestic Product |
| `UNRATE` | Unemployment Rate |
| `CPIAUCSL` | Consumer Price Index (CPI) |
| `PCEPI` | PCE Price Index (the Fed's preferred inflation gauge) |
| `FEDFUNDS` | Federal Funds Rate |
| `DGS10` | 10-Year Treasury Yield |
| `T10Y2Y` | 10-Year minus 2-Year Treasury Spread |
| `PAYEMS` | Nonfarm Payrolls |
| `MORTGAGE30US` | 30-Year Fixed Mortgage Rate |
| `UMCSENT` | Consumer Sentiment (University of Michigan) |

## 💬 Example Prompts

Once the server is connected, just ask Claude:

- "How's the U.S. economy doing right now?"
- "What's the current unemployment rate?"
- "Show me year-over-year CPI inflation for the last 12 months."
- "What's the 10-year Treasury yield, and how has it moved this year?"
- "Find FRED series about consumer credit."
- "What's the 10Y-2Y yield spread? Is the yield curve inverted?"
- "Compare real GDP growth over the last 8 quarters."
- "What does the PCEPI series measure, and how often is it updated?"

### Example output

Asking *"What's year-over-year CPI inflation for the last few months?"* runs
`get_series_observations` with `series_id=CPIAUCSL`, `units=pc1`:

```markdown
# Consumer Price Index for All Urban Consumers: All Items (CPIAUCSL)

**Units:** Percent change from year ago · **Frequency:** m
**Total observations:** 940

**Latest:** 3.39 (2026-04-01)

| Date       | Value |
|------------|-------|
| 2026-04-01 | 3.39  |
| 2026-03-01 | 3.29  |
| 2026-02-01 | 2.43  |
```

## 🐛 Troubleshooting

**"No FRED API key configured"**
Set `FRED_API_KEY` in your MCP client config (see Quick Start) to a free key from [fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys), then restart the client.

**"Command not found" / "Python not found"**
Make sure Python 3.10+ and Node.js 16+ are installed and on your PATH. On macOS/Linux, try `python3`.

**"FRED is rate-limiting requests"**
FRED allows 120 requests/minute per key. The server retries automatically; if you still hit it, wait a minute.

**Tools not showing up in Claude**
1. Confirm the config file is valid JSON (no trailing commas).
2. Fully quit and reopen Claude Desktop.
3. Check that `FRED_API_KEY` is set in the server's `env` block.

**"FRED rejected the request"**
The series ID is probably wrong. Use `search_series` to find the correct ID, or `get_series_info` to confirm a series exists.

## 🛠️ Manual Installation (Alternative)

If you would rather run the Python file directly instead of via npx:

**1. Download the server and install the dependency**

Save `fred_mcp.py` somewhere on your machine, then:

```bash
pip install mcp
```

(or `pip3` on macOS/Linux)

**2. Point Claude Desktop at it**

```json
{
  "mcpServers": {
    "fred": {
      "command": "python3",
      "args": ["/absolute/path/to/fred_mcp.py"],
      "env": { "FRED_API_KEY": "your_key_here" }
    }
  }
}
```

On Windows use `"command": "python"` and a path like `"C:\\path\\to\\fred_mcp.py"` (double backslashes or forward slashes).

**3. Restart Claude Desktop.**

## 🔒 Privacy & Rate Limits

- Uses the official [FRED API](https://fred.stlouisfed.org/docs/api/fred/) with your own free API key.
- Requests go straight from your machine to FRED. Nothing is stored or proxied.
- FRED rate-limits **120 requests/minute per key**; the server retries with backoff on `429`.
- Intended for personal, educational, and research use.

## 📝 Notes

- Series IDs are case-insensitive here (they're upper-cased for you), e.g. `unrate` works.
- FRED marks missing observations with `.`; those are shown as `N/A`.
- The `units` transforms (e.g. `pc1` for year-over-year %) are computed by FRED, so the values are authoritative — no client-side math.
- Data coverage and frequency vary by series; use `get_series_info` to check before pulling a range.

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## 📚 Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FRED API documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [Get a FRED API key](https://fredaccount.stlouisfed.org/apikeys)

## ⚖️ Legal Disclaimer

This tool uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis. FRED® is a registered trademark of the Federal Reserve Bank of St. Louis. Use of the FRED API is subject to its [Terms of Use](https://fred.stlouisfed.org/docs/api/terms_of_use.html).

## 👤 Author

**Daniel Shashko**
- GitHub: [@danishashko](https://github.com/danishashko)
- LinkedIn: [daniel-shashko](https://linkedin.com/in/daniel-shashko)
- npm: [danielshashko](https://www.npmjs.com/~danielshashko)

## 📄 License

MIT © Daniel Shashko
