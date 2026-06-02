# FRED MCP Server 📊

[![npm version](https://img.shields.io/npm/v/fred-mcp-server.svg)](https://www.npmjs.com/package/fred-mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/fred-mcp-server.svg)](https://www.npmjs.com/package/fred-mcp-server)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

U.S. and global economic data for Claude Desktop and any MCP-compatible client, powered by [FRED](https://fred.stlouisfed.org) (Federal Reserve Economic Data). Search and pull from **800,000+ economic time series** — GDP, inflation, unemployment, interest rates, and more — all from natural language.

> **npm package:** [`fred-mcp-server`](https://www.npmjs.com/package/fred-mcp-server) &nbsp;·&nbsp; **GitHub repo:** [`danishashko/fred-mcp`](https://github.com/danishashko/fred-mcp). The repo name is shorter than the package name; both refer to this project.

## 🎯 What You Get

- 🔎 **Search** 800k+ economic series by keyword
- 📈 **Observations** with built-in transforms (levels, % change, year-over-year) and frequency aggregation (daily → monthly/quarterly/annual)
- 🧾 **Series metadata** — units, frequency, seasonal adjustment, coverage, notes
- 🇺🇸 **Economic snapshot** — key U.S. indicators in one call
- 🗂️ **Category browsing** to discover data by topic
- 🗓️ **Releases** tracked by FRED

Every tool returns human-readable **markdown** by default, or structured **JSON** on request (`response_format: "json"`).

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
      "args": ["-y", "fred-mcp-server"],
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
npm install -g fred-mcp-server
```

```json
{
  "mcpServers": {
    "fred": {
      "command": "fred-mcp-server",
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

## 💬 Example Prompts

Once the server is connected, just ask Claude:

- "How's the U.S. economy doing right now?"
- "What's the current unemployment rate?"
- "Show me year-over-year CPI inflation for the last 12 months."
- "What's the 10-year Treasury yield, and how has it moved this year?"
- "Find FRED series about consumer credit."
- "What's the 10Y-2Y yield spread? Is the curve inverted?"

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

## 🛠️ Manual Installation (Alternative)

If you would rather run the Python file directly instead of via npx:

```bash
pip install mcp
export FRED_API_KEY=your_key_here   # Windows: set FRED_API_KEY=your_key_here
```

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
