#!/usr/bin/env python3
"""
FRED MCP Server - Installation Test Script

Verifies Python version, the `mcp` dependency, that the server file is valid,
and (if FRED_API_KEY is set) that the FRED API is reachable.
"""

import os
import sys

print("=" * 60)
print("FRED MCP Server - Installation Test")
print("=" * 60)
print()

# Test 1: Python version
print("Test 1: Checking Python version...")
v = sys.version_info
if v.major > 3 or (v.major == 3 and v.minor >= 10):
    print(f"OK  Python {v.major}.{v.minor}.{v.micro}")
else:
    print(f"FAIL Python {v.major}.{v.minor}.{v.micro} - need 3.10+")
    sys.exit(1)
print()

# Test 2: Dependency
print("Test 2: Checking required packages...")
ok = True
try:
    import mcp  # noqa: F401

    print("OK  mcp - installed")
except ImportError:
    print("FAIL mcp - NOT installed (run: pip install -r requirements.txt)")
    ok = False
print()

# Test 3: Server file valid
print("Test 3: Checking server file...")
server = "fred_mcp.py"
if os.path.exists(server):
    try:
        with open(server, "r", encoding="utf-8") as f:
            compile(f.read(), server, "exec")
        print(f"OK  {server} - valid Python syntax")
    except SyntaxError as e:
        print(f"FAIL {server} - syntax error: {e}")
        ok = False
else:
    print(f"FAIL {server} - not found")
    ok = False
print()

# Test 4: API key + connectivity (optional)
print("Test 4: Checking FRED API key and connectivity...")
key = os.environ.get("FRED_API_KEY", "").strip()
if not key:
    print("WARN FRED_API_KEY not set - set it before using the server")
    print("     Get a free key at https://fredaccount.stlouisfed.org/apikeys")
else:
    import json
    import urllib.request

    try:
        url = (
            "https://api.stlouisfed.org/fred/series?series_id=GDP"
            f"&api_key={key}&file_type=json"
        )
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        title = data["seriess"][0]["title"]
        print(f"OK  FRED API reachable (fetched: {title})")
    except Exception as e:
        print(f"FAIL Could not reach FRED API: {e}")
        ok = False
print()

print("=" * 60)
print("All checks passed!" if ok else "Some checks failed - see above.")
print("=" * 60)
sys.exit(0 if ok else 1)
