# Put Diagonal Candidate Screener

A local web dashboard that screens a watchlist against your put-diagonal
entry criteria using live Yahoo Finance data.

## What it checks

| Check | Source | Reliability |
|---|---|---|
| RSI(14) < 30 (oversold) | Yahoo OHLCV | High — computed directly |
| Price above 50-day SMA | Yahoo OHLCV | High — computed directly |
| Prior bounce off lower Bollinger Band (20d lookback) | Yahoo OHLCV | High — computed directly |
| IV > 50% | Yahoo options chain | Low-medium — Yahoo's IV calc, often stale/missing for thin names |
| Front-month IV > back-month IV (backwardation) | Yahoo options chain | Low-medium — same caveat |
| 20-day avg volume > 1,000,000 | Yahoo OHLCV | High |
| Tight bid/ask spread (≤10% of mid) | Yahoo options chain | Low — Yahoo quotes can be stale outside market hours |

**Not yet included / needs your broker to verify before trading:**
delta-based strike selection, strike width ≤ $7, net theta, net debit
as % of premium. These need real-time greeks from a broker feed
(Yahoo doesn't reliably provide delta/theta) — see `put_diagonal_scanner_broker_template.py`
from earlier in this project for that logic, ready to wire to TastyTrade
or similar once you have an account with API access.

## Setup

```bash
pip install -r requirements.txt
python server.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Use

1. Paste tickers into the box (comma or space separated, e.g. `AAPL MSFT NVDA`)
2. Click **Scan** (or Cmd/Ctrl+Enter)
3. Green PASS rows met every check Yahoo had data for. Amber dots mean
   "no data available" — not a fail, just unknown — so PASS does not
   necessarily mean every single one of your 7 criteria was confirmed.
   Expand "raw values" on any row to see the underlying numbers.

## Known limitations

- Yahoo Finance has no official SLA and can rate-limit or change format
  without notice — if scans start failing, that's the likely cause.
- Capped at 50 tickers per scan to keep response times reasonable; Yahoo
  options chain lookups are the slow part (one extra request per symbol).
- This screens **candidates only**. It does not place orders, does not
  select specific strikes/expirations for entry, and does not know your
  account size or risk limits. Treat it as a first-pass filter, not a
  trade signal.
