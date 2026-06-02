# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-06-02

Packaging only. No runtime code changes.

### Added

- `server.json` and an `mcpName` field for listing on the official MCP Registry.

## [1.0.1] - 2026-06-02

Documentation only. No runtime code changes from 1.0.0.

### Changed

- Expanded the README: a popular-series quick-reference table, example tool
  output, numbered manual-install steps, a Privacy & Rate Limits section, and
  usage notes.

## [1.0.0] - 2026-06-02

Initial release. Every tool was verified end to end by driving the real MCP
server over stdio against the live FRED API.

### Added

- **`search_series`** — find economic data series by keyword, ordered by
  popularity (the discovery entry point).
- **`get_series_observations`** — the core data tool: actual values for any
  series, with FRED's built-in transformations (percent change, year-over-year,
  etc.) and frequency aggregation (daily → weekly/monthly/quarterly/annual).
- **`get_series_info`** — full metadata for a series (units, frequency, seasonal
  adjustment, coverage, descriptive notes).
- **`get_economic_snapshot`** — one call returns the latest value of key U.S.
  indicators (real GDP, unemployment, CPI, PCE, Fed funds, 10Y Treasury, the
  10Y-2Y spread, payrolls, mortgage rate, consumer sentiment, housing starts).
- **`browse_category`** — navigate FRED's category tree to discover data by
  topic.
- **`get_releases`** — list the economic data releases FRED tracks.
- **`npx -y fred-economic-mcp`** launcher (`bin/cli.js`) that finds Python 3.10+,
  builds an isolated virtual environment, installs dependencies on first run,
  and passes `FRED_API_KEY` through to the server.
- Built-in retry/backoff for FRED's 120-requests/minute rate limit, and clear,
  specific error messages (including a missing-API-key guide).

[1.0.1]: https://github.com/danishashko/fred-economic-mcp/releases/tag/v1.0.1
[1.0.0]: https://github.com/danishashko/fred-economic-mcp/releases/tag/v1.0.0
