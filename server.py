"""
Put Diagonal Screener — Local Web App
======================================

Run locally:
    pip install yfinance flask
    python server.py
Then open http://127.0.0.1:5000 in your browser.

DATA SOURCE NOTES (read before trusting any output):
- Price/volume/RSI/SMA/Bollinger: pulled live from Yahoo Finance via yfinance.
  This is free, no signup, generally reliable for daily OHLCV.
- Options IV / term structure / delta / bid-ask: Yahoo's options endpoint is
  thin and inconsistent. We pull what it gives us (bid, ask, IV from Yahoo's
  own calc) and clearly label fields as "Yahoo-estimated" in the UI. Yahoo
  does NOT provide greeks (delta, theta) directly — we approximate delta
  with Black-Scholes from Yahoo's IV, which is a rough estimate, not what
  your broker would show you. Do not treat options-derived fields here as
  trade-ready; verify against your broker before acting on them.
"""

import math
from datetime import date, datetime, timedelta

from flask import Flask, jsonify, request, send_from_directory

try:
    import yfinance as yf
except ImportError:
    yf = None

app = Flask(__name__, static_folder="static")


# ---------------------------------------------------------------------------
# S&P 500 ticker list (snapshot as of June 2026, sourced from the
# datasets/s-and-p-500-companies public dataset on GitHub, which tracks
# Wikipedia's maintained constituent list). Index membership changes over
# time (additions/removals run a few times a year) - this snapshot will
# drift slowly out of date. Treat it as "close enough" for screening, not
# as an authoritative, always-current source.
# ---------------------------------------------------------------------------

SP500_TICKERS = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB","AKAM","ALB","ARE",
    "ALGN","ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN","AMCR","AEE","AEP","AXP","AIG","AMT","AWK",
    "AMP","AME","AMGN","APH","ADI","AON","APA","APO","AAPL","AMAT","APP","APTV","ACGL","ADM","ARES",
    "ANET","AJG","AIZ","T","ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC","BAX","BDX",
    "BRK.B","BBY","TECH","BIIB","BLK","BX","XYZ","BK","BA","BKNG","BSX","BMY","AVGO","BR","BRO","BF.B",
    "BLDR","BG","BXP","CHRW","CDNS","CPT","CPB","COF","CAH","CCL","CARR","CVNA","CASY","CAT","CBOE",
    "CBRE","CDW","COR","CNC","CNP","CF","CRL","SCHW","CHTR","CVX","CMG","CB","CHD","CIEN","CI","CINF",
    "CTAS","CSCO","C","CFG","CLX","CME","CMS","KO","CTSH","COHR","COIN","CL","CMCSA","FIX","CAG","COP",
    "ED","STZ","CEG","COO","CPRT","GLW","CPAY","CTVA","CSGP","COST","CTRA","CRH","CRWD","CCI","CSX",
    "CMI","CVS","DHR","DRI","DDOG","DVA","DECK","DE","DELL","DAL","DVN","DXCM","FANG","DLR","DG","DLTR",
    "D","DPZ","DASH","DOV","DOW","DHI","DTE","DUK","DD","ETN","EBAY","SATS","ECL","EIX","EW","EA","ELV",
    "EME","EMR","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR","ERIE","ESS","EL","EG","EVRG","ES","EXC",
    "EXE","EXPE","EXPD","EXR","XOM","FFIV","FDS","FICO","FAST","FRT","FDX","FIS","FITB","FSLR","FE",
    "FISV","F","FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT","GE","GEHC","GEV","GEN","GNRC","GD",
    "GIS","GM","GPC","GILD","GPN","GL","GDDY","GS","HAL","HIG","HAS","HCA","DOC","HSIC","HSY","HPE",
    "HLT","HD","HON","HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX","IDXX","ITW","INCY",
    "IR","PODD","INTC","IBKR","ICE","IFF","IP","INTU","ISRG","IVZ","INVH","IQV","IRM","JBHT","JBL",
    "JKHY","J","JNJ","JCI","JPM","KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KKR","KLAC","KHC","KR",
    "LHX","LH","LRCX","LVS","LDOS","LEN","LII","LLY","LIN","LYV","LMT","L","LOW","LULU","LITE","LYB",
    "MTB","MPC","MAR","MRSH","MLM","MAS","MA","MKC","MCD","MCK","MDT","MRK","META","MET","MTD","MGM",
    "MCHP","MU","MSFT","MAA","MRNA","TAP","MDLZ","MPWR","MNST","MCO","MS","MOS","MSI","MSCI","NDAQ",
    "NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC","NTRS","NOC","NCLH","NRG","NUE",
    "NVDA","NVR","NXPI","ORLY","OXY","ODFL","OMC","ON","OKE","ORCL","OTIS","PCAR","PKG","PLTR","PANW",
    "PSKY","PH","PAYX","PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC","POOL","PPG","PPL","PFG",
    "PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","PWR","QCOM","DGX","Q","RL","RJF","RTX","O","REG",
    "REGN","RF","RSG","RMD","RVTY","HOOD","ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SNDK","SBAC",
    "SLB","STX","SRE","NOW","SHW","SPG","SWKS","SJM","SW","SNA","SOLV","SO","LUV","SWK","SBUX","STT",
    "STLD","STE","SYK","SMCI","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT","TEL","TDY",
    "TER","TSLA","TXN","TPL","TXT","TMO","TJX","TKO","TTD","TSCO","TT","TDG","TRV","TRMB","TFC","TYL",
    "TSN","USB","UBER","UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO","VTR","VLTO","VRSN",
    "VRSK","VZ","VRTX","VRT","VTRS","VICI","V","VST","VMC","WRB","GWW","WAB","WMT","DIS","WBD","WM",
    "WAT","WEC","WFC","WELL","WST","WDC","WY","WSM","WMB","WTW","WDAY","WYNN","XEL","XYL","YUM","ZBRA",
    "ZBH","ZTS",
]

SP500_SOURCE_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"


def get_sp500_tickers():
    """Try to fetch a fresh list from GitHub; fall back to the baked-in
    snapshot above if that fails (offline, GitHub down, format changed)."""
    try:
        import urllib.request
        req = urllib.request.Request(SP500_SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8")
        lines = text.strip().split("\n")[1:]
        tickers = [line.split(",")[0].strip() for line in lines if line.strip()]
        if len(tickers) > 400:
            return tickers, "live"
    except Exception:
        pass
    return SP500_TICKERS, "snapshot"


# ---------------------------------------------------------------------------
# Config — your stated screening thresholds
# ---------------------------------------------------------------------------

class Config:
    RSI_PERIOD = 14
    RSI_OVERSOLD_MAX = 40  # oversold threshold: RSI <= 40

    SMA_TREND_PERIOD = 50

    UPTREND_LONG_SMA_PERIOD = 200   # classic uptrend structure: price > 50 SMA AND 50 SMA > 200 SMA
    HISTORY_PERIOD = "1y"            # fetch window; needs 200+ trading days for the long SMA, ~1y gives margin

    BOLLINGER_PERIOD = 20
    BOLLINGER_STD = 2
    BOLLINGER_BOUNCE_LOOKBACK_DAYS = 20

    FIB_SWING_LOOKBACK_DAYS = 90       # window used to find the swing high/low
    FIB_BOUNCE_LOOKBACK_DAYS = 20       # window to check for a recent bounce, same as Bollinger
    FIB_TOLERANCE_PCT = 0.025           # 2.5% band around each Fib level counts as a "touch"

    IV_MIN = 50.0  # percent

    ANALYST_BUY_PCT_MIN = 0.75  # (strongBuy + buy) / total ratings must be >= this

    MIN_AVG_DAILY_VOLUME = 1_000_000

    MAX_BID_ASK_SPREAD_PCT = 0.10  # 10% of mid — Yahoo quotes are wide/stale, looser than a real broker feed

    SHORT_DELTA_MIN = 0.20
    SHORT_DELTA_MAX = 0.30
    LONG_DELTA_MIN = 0.40
    LONG_DELTA_MAX = 0.60

    MAX_STRIKE_WIDTH = 7.00

    MIN_CRITERIA_PASS = 8   # out of 10 total criteria — both the pass bar and the display cutoff
    TOTAL_CRITERIA = 10


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_sma(closes, period):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_bollinger(closes, period=20, num_std=2):
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    sma = sum(window) / period
    variance = sum((c - sma) ** 2 for c in window) / period
    std = variance ** 0.5
    return sma - num_std * std, sma, sma + num_std * std


def has_bounced_off_lower_band(closes, lookback_days, period=20, num_std=2):
    """Looks back over `lookback_days`: did price close at/below the lower
    band at some point, then later close back above it? Rough definition —
    see playbook for the open question on what 'bounce' should mean exactly."""
    if len(closes) < period + lookback_days:
        return False
    touched = False
    start = len(closes) - lookback_days
    for i in range(start, len(closes)):
        window = closes[max(0, i - period):i]
        if len(window) < period:
            continue
        lower, _, _ = compute_bollinger(window, period, num_std)
        if lower is None:
            continue
        if closes[i] <= lower:
            touched = True
        elif touched and closes[i] > lower:
            return True
    return False


def compute_fib_levels(swing_high, swing_low):
    """Standard retracement levels measured down from a swing high toward a
    swing low (i.e. this assumes the recent leg was a decline — the levels
    represent potential support on the way back down, or resistance on a
    bounce back up). Returns a dict of level name -> price."""
    diff = swing_high - swing_low
    return {
        "0.0": swing_high,
        "0.382": swing_high - 0.382 * diff,
        "0.5": swing_high - 0.5 * diff,
        "0.618": swing_high - 0.618 * diff,
        "1.0": swing_low,
    }


def has_bounced_off_fib_level(highs, lows, closes, lookback_days, swing_lookback=90, tolerance_pct=0.025):
    """
    Checks whether price recently bounced off the 38.2%, 50%, or 61.8%
    Fibonacci retracement level.

    Methodology:
    1. Find the swing high and swing low over `swing_lookback` trading days
       (roughly 3-6 months) to define the retracement range.
    2. Compute the 38.2 / 50 / 61.8 levels from that swing.
    3. Over the last `lookback_days`, check for a "touch and recover":
       the day's LOW dipped to within `tolerance_pct` of a level (or below
       it), and the day's CLOSE (same day or the next day) recovered back
       above the level minus the tolerance band.

    Returns (bounced: bool, details: dict) where details includes the swing
    high/low used, the computed levels, and which level (if any) triggered
    the bounce — useful for showing the user why a stock passed.
    """
    if len(closes) < swing_lookback or len(highs) < swing_lookback or len(lows) < swing_lookback:
        return False, {}

    swing_window_highs = highs[-swing_lookback:]
    swing_window_lows = lows[-swing_lookback:]
    swing_high = max(swing_window_highs)
    swing_low = min(swing_window_lows)

    if swing_high <= swing_low:
        return False, {}

    levels = compute_fib_levels(swing_high, swing_low)
    watch_levels = {k: v for k, v in levels.items() if k in ("0.382", "0.5", "0.618")}

    start = max(0, len(closes) - lookback_days)
    n = len(closes)

    for level_name, level_price in watch_levels.items():
        band = level_price * tolerance_pct
        lower_bound = level_price - band
        upper_bound = level_price + band

        for i in range(start, n):
            day_low = lows[i]
            # "Touched" the level: low dipped to/below the upper edge of the band
            if day_low <= upper_bound:
                # Look for recovery same day or next day: close back above
                # the lower edge of the band (i.e. didn't just keep falling)
                recovered = closes[i] >= lower_bound
                if not recovered and i + 1 < n:
                    recovered = closes[i + 1] >= lower_bound
                if recovered:
                    return True, {
                        "swing_high": round(swing_high, 2),
                        "swing_low": round(swing_low, 2),
                        "level": level_name,
                        "level_price": round(level_price, 2),
                    }

    return False, {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
    }


def black_scholes_put_delta(S, K, T, r, sigma):
    """Rough delta estimate. T in years, sigma as decimal (e.g. 0.55 for 55%)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return None
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        # N(d1) via erf
        Nd1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        return Nd1 - 1  # put delta is negative
    except (ValueError, ZeroDivisionError):
        return None


def _pick_expiration_in_dte_range(expirations, min_dte, max_dte):
    """Given a list of expiration date strings (YYYY-MM-DD), return the one
    whose DTE falls inside [min_dte, max_dte], preferring the one closest to
    the midpoint of that range. Returns None if nothing qualifies."""
    today = date.today()
    candidates = []
    for exp_str in expirations:
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        dte = (exp_date - today).days
        if min_dte <= dte <= max_dte:
            candidates.append((exp_str, dte))
    if not candidates:
        return None
    midpoint = (min_dte + max_dte) / 2
    candidates.sort(key=lambda c: abs(c[1] - midpoint))
    return candidates[0][0]


def suggest_diagonal_strikes(ticker, last_close, cfg=Config()):
    """
    Best-effort suggestion of which put strikes to use for the diagonal,
    given Yahoo's options data:
      - SHORT leg: nearest weekly/Friday expiration, strike near the
        20-30 delta band (approximated via Black-Scholes from Yahoo's IV,
        since Yahoo doesn't expose real broker greeks).
      - LONG leg: an expiration genuinely in the 30-45 DTE window, strike
        near the 40-60 delta band.

    Returns a dict with both legs' details (or error notes if data was
    unavailable), plus an explicit warning that deltas are approximated,
    not the real, broker-calculated greeks.
    """
    result = {
        "short_leg": None,
        "long_leg": None,
        "note": "Strikes and deltas are ROUGH ESTIMATES derived from Yahoo's "
                "implied volatility via Black-Scholes, not real broker greeks. "
                "Verify against your broker's option chain before placing any trade.",
    }

    try:
        expirations = list(ticker.options)
    except Exception as e:
        result["error"] = f"Could not fetch expirations: {e}"
        return result

    if not expirations:
        result["error"] = "No options chain available for this symbol"
        return result

    today = date.today()
    r = 0.045  # rough risk-free rate assumption for the BS approximation

    def build_leg(exp_str, target_delta_min, target_delta_max):
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            T = dte / 365.0
            chain = ticker.option_chain(exp_str)
            puts = chain.puts
            if puts.empty:
                return {"expiration": exp_str, "dte": dte, "error": "No puts in chain"}

            puts = puts.copy()
            target_mid = (target_delta_min + target_delta_max) / 2

            def est_delta(row):
                iv = row.get("impliedVolatility")
                if not iv or iv <= 0:
                    return None
                d = black_scholes_put_delta(last_close, row["strike"], T, r, float(iv))
                return abs(d) if d is not None else None

            puts["est_delta"] = puts.apply(est_delta, axis=1)
            valid = puts.dropna(subset=["est_delta"])
            if valid.empty:
                return {"expiration": exp_str, "dte": dte, "error": "Could not estimate deltas (missing IV)"}

            valid = valid.copy()
            valid["delta_diff"] = (valid["est_delta"] - target_mid).abs()
            best = valid.loc[valid["delta_diff"].idxmin()]

            bid = float(best["bid"]) if best["bid"] else 0.0
            ask = float(best["ask"]) if best["ask"] else 0.0
            in_band = target_delta_min <= best["est_delta"] <= target_delta_max

            return {
                "expiration": exp_str,
                "dte": dte,
                "strike": round(float(best["strike"]), 2),
                "est_delta": round(float(best["est_delta"]), 3),
                "in_target_band": bool(in_band),
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "mid": round((bid + ask) / 2, 2) if (bid or ask) else None,
                "iv_pct": round(float(best["impliedVolatility"]) * 100, 1) if best["impliedVolatility"] else None,
            }
        except Exception as e:
            return {"expiration": exp_str, "error": str(e)}

    # Short leg: nearest expiration (this week's Friday, or closest available)
    short_exp = expirations[0]
    result["short_leg"] = build_leg(short_exp, cfg.SHORT_DELTA_MIN, cfg.SHORT_DELTA_MAX)

    # Long leg: genuinely 30-45 DTE, not just "a few slots out"
    long_exp = _pick_expiration_in_dte_range(expirations, 30, 45)
    if long_exp is None:
        result["long_leg"] = {"error": "No expiration found in the 30-45 DTE window for this symbol"}
    else:
        result["long_leg"] = build_leg(long_exp, cfg.LONG_DELTA_MIN, cfg.LONG_DELTA_MAX)

    # Strike width check, only if both legs resolved cleanly
    if (result["short_leg"] and "strike" in result["short_leg"]
            and result["long_leg"] and "strike" in result["long_leg"]):
        width = result["long_leg"]["strike"] - result["short_leg"]["strike"]
        result["strike_width"] = round(width, 2)
        result["within_max_width"] = abs(width) <= cfg.MAX_STRIKE_WIDTH

    return result


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------

def screen_symbol(symbol, cfg=Config()):
    if yf is None:
        return {"symbol": symbol, "error": "yfinance not installed. Run: pip install yfinance"}

    result = {"symbol": symbol, "checks": {}, "values": {}, "error": None}

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=cfg.HISTORY_PERIOD)
        if hist.empty or len(hist) < 60:
            result["error"] = "Insufficient price history"
            return result

        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        last_close = closes[-1]

        # --- Technicals (real, computed from Yahoo OHLCV) ---
        rsi = compute_rsi(closes, cfg.RSI_PERIOD)
        sma50 = compute_sma(closes, cfg.SMA_TREND_PERIOD)
        sma200 = compute_sma(closes, cfg.UPTREND_LONG_SMA_PERIOD)
        bounce = has_bounced_off_lower_band(closes, cfg.BOLLINGER_BOUNCE_LOOKBACK_DAYS,
                                             cfg.BOLLINGER_PERIOD, cfg.BOLLINGER_STD)
        fib_bounce, fib_detail = has_bounced_off_fib_level(
            highs, lows, closes,
            cfg.FIB_BOUNCE_LOOKBACK_DAYS,
            cfg.FIB_SWING_LOOKBACK_DAYS,
            cfg.FIB_TOLERANCE_PCT,
        )
        avg_vol_20 = sum(volumes[-20:]) / min(20, len(volumes))

        result["values"]["last_close"] = round(last_close, 2)
        result["values"]["rsi"] = rsi
        result["values"]["sma50"] = round(sma50, 2) if sma50 else None
        result["values"]["sma200"] = round(sma200, 2) if sma200 else None
        result["values"]["avg_volume_20d"] = int(avg_vol_20)
        result["values"]["fib_swing_high"] = fib_detail.get("swing_high")
        result["values"]["fib_swing_low"] = fib_detail.get("swing_low")
        result["values"]["fib_bounce_level"] = fib_detail.get("level")
        result["values"]["fib_bounce_price"] = fib_detail.get("level_price")

        result["checks"]["rsi_oversold"] = (rsi is not None and rsi <= cfg.RSI_OVERSOLD_MAX)
        result["checks"]["above_50sma"] = (sma50 is not None and last_close > sma50)
        # Uptrend = classic trend structure: price above the 50-day SMA AND
        # the 50-day SMA above the 200-day SMA. This is a separate, stricter
        # check than above_50sma alone - a stock can be above its 50 SMA
        # during a short-term bounce inside a longer downtrend, which this
        # check is meant to filter out.
        result["checks"]["uptrend"] = (
            sma50 is not None and sma200 is not None
            and last_close > sma50 and sma50 > sma200
        )
        result["checks"]["bollinger_bounce_history"] = bounce
        result["checks"]["fib_bounce_history"] = fib_bounce
        result["checks"]["volume_above_min"] = avg_vol_20 > cfg.MIN_AVG_DAILY_VOLUME

        # --- Options-derived fields (Yahoo-estimated, lower confidence) ---
        iv_current = None
        iv_short = None
        iv_long = None
        spread_ok = None
        try:
            expirations = ticker.options
            if expirations:
                near_exp = expirations[0]
                chain = ticker.option_chain(near_exp)
                puts = chain.puts
                if not puts.empty:
                    # ATM put = closest strike to last_close
                    puts = puts.copy()
                    puts["strike_diff"] = (puts["strike"] - last_close).abs()
                    atm = puts.loc[puts["strike_diff"].idxmin()]
                    iv_current = round(float(atm["impliedVolatility"]) * 100, 1) if atm["impliedVolatility"] else None
                    bid, ask = float(atm["bid"]), float(atm["ask"])
                    mid = (bid + ask) / 2
                    if mid > 0:
                        spread_ok = ((ask - bid) / mid) <= cfg.MAX_BID_ASK_SPREAD_PCT

                if len(expirations) > 3:
                    far_exp = expirations[min(6, len(expirations) - 1)]  # rough "longer-dated" pick
                    far_chain = ticker.option_chain(far_exp)
                    far_puts = far_chain.puts
                    if not far_puts.empty:
                        far_puts = far_puts.copy()
                        far_puts["strike_diff"] = (far_puts["strike"] - last_close).abs()
                        far_atm = far_puts.loc[far_puts["strike_diff"].idxmin()]
                        if far_atm["impliedVolatility"]:
                            iv_long = round(float(far_atm["impliedVolatility"]) * 100, 1)
                iv_short = iv_current
        except Exception as opt_err:
            result["values"]["options_note"] = f"Options data unavailable: {opt_err}"

        result["values"]["iv_current_pct"] = iv_current
        result["values"]["iv_short_term_pct"] = iv_short
        result["values"]["iv_long_term_pct"] = iv_long
        result["values"]["bid_ask_tight"] = spread_ok

        result["checks"]["iv_above_50"] = (iv_current is not None and iv_current > cfg.IV_MIN)
        result["checks"]["term_structure_backwardation"] = (
            iv_short is not None and iv_long is not None and iv_short > iv_long
        )
        result["checks"]["bid_ask_tight"] = spread_ok if spread_ok is not None else None

        # --- Analyst sentiment (Yahoo's recommendation breakdown) ---
        buy_pct = None
        total_ratings = None
        try:
            recs = ticker.recommendations
            if recs is not None and not recs.empty:
                # Most recent period is typically '0m' (current month); use
                # the first row, which yfinance returns as most-recent-first.
                row = recs.iloc[0]
                strong_buy = int(row.get("strongBuy", 0) or 0)
                buy = int(row.get("buy", 0) or 0)
                hold = int(row.get("hold", 0) or 0)
                sell = int(row.get("sell", 0) or 0)
                strong_sell = int(row.get("strongSell", 0) or 0)
                total_ratings = strong_buy + buy + hold + sell + strong_sell
                if total_ratings > 0:
                    buy_pct = round((strong_buy + buy) / total_ratings, 4)
        except Exception as rec_err:
            result["values"]["analyst_note"] = f"Analyst data unavailable: {rec_err}"

        result["values"]["analyst_buy_pct"] = round(buy_pct * 100, 1) if buy_pct is not None else None
        result["values"]["analyst_total_ratings"] = total_ratings

        result["checks"]["analyst_sentiment"] = (
            (buy_pct is not None and total_ratings is not None and total_ratings > 0)
            and (buy_pct >= cfg.ANALYST_BUY_PCT_MIN)
        ) if buy_pct is not None else None

        # Overall pass: at least MIN_CRITERIA_PASS of TOTAL_CRITERIA checks
        # must be confirmed positive. Checks that are None (missing data,
        # e.g. thin options chain or no analyst coverage) are excluded from
        # the denominator rather than counted as a fail - but at least
        # MIN_CRITERIA_PASS checks must have actually been evaluated, or a
        # PASS would be claiming more confidence than the data supports.
        evaluated = [v for v in result["checks"].values() if v is not None]
        passed_count = sum(1 for v in evaluated if v is True)
        result["passed"] = len(evaluated) >= cfg.MIN_CRITERIA_PASS and passed_count >= cfg.MIN_CRITERIA_PASS
        result["checks_passed_count"] = passed_count
        result["checks_evaluated_count"] = len(evaluated)
        result["missing_data"] = [k for k, v in result["checks"].items() if v is None]

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


def build_detail_payload(symbol, cfg=Config()):
    """
    Builds the full data package for the symbol detail modal: daily OHLC
    history, a rolling Bollinger Band series (so the chart can draw the
    actual bands over time, not just today's snapshot), the Fibonacci
    levels/swing used in screening, and the same screening result (values +
    checks) returned by screen_symbol, so the modal and the table never
    disagree about what passed.
    """
    if yf is None:
        return {"symbol": symbol, "error": "yfinance not installed. Run: pip install yfinance"}

    screening = screen_symbol(symbol, cfg)
    payload = {"symbol": symbol, "screening": screening, "error": None}

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=cfg.HISTORY_PERIOD)
        if hist.empty:
            payload["error"] = "Insufficient price history"
            return payload

        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()

        # Rolling Bollinger series - one (lower, mid, upper) triple per day,
        # once enough history has accumulated to compute a 20-day window.
        bb_series = []
        for i in range(len(closes)):
            window = closes[max(0, i - cfg.BOLLINGER_PERIOD + 1):i + 1]
            if len(window) < cfg.BOLLINGER_PERIOD:
                bb_series.append({"lower": None, "mid": None, "upper": None})
                continue
            lower, mid, upper = compute_bollinger(window, cfg.BOLLINGER_PERIOD, cfg.BOLLINGER_STD)
            bb_series.append({
                "lower": round(lower, 2),
                "mid": round(mid, 2),
                "upper": round(upper, 2),
            })

        # Fib levels from the same swing window used in screening, so the
        # chart's horizontal lines match exactly what screen_symbol checked.
        fib_bounce, fib_detail = has_bounced_off_fib_level(
            highs, lows, closes,
            cfg.FIB_BOUNCE_LOOKBACK_DAYS, cfg.FIB_SWING_LOOKBACK_DAYS, cfg.FIB_TOLERANCE_PCT,
        )
        fib_levels = None
        if fib_detail.get("swing_high") and fib_detail.get("swing_low"):
            fib_levels = compute_fib_levels(fib_detail["swing_high"], fib_detail["swing_low"])

        payload["chart"] = {
            "dates": dates,
            "closes": [round(c, 2) for c in closes],
            "highs": [round(h, 2) for h in highs],
            "lows": [round(l, 2) for l in lows],
            "bollinger": bb_series,
            "fib_levels": fib_levels,
            "fib_swing_high": fib_detail.get("swing_high"),
            "fib_swing_low": fib_detail.get("swing_low"),
        }

        last_close = closes[-1]
        payload["suggested_strikes"] = suggest_diagonal_strikes(ticker, last_close, cfg)
    except Exception as e:
        payload["error"] = str(e)

    return payload


def _filter_to_passing(results):
    """Keep stocks that met the pass bar, plus any that errored out (so the
    user can still see fetch failures rather than have them silently
    vanish). Stocks that screened cleanly but didn't meet the bar are
    dropped from the response entirely, per the 8-of-10 display cutoff."""
    return [r for r in results if r.get("passed") or r.get("error")]


@app.route("/api/detail/<symbol>", methods=["GET"])
def api_detail(symbol):
    """Returns full chart data + screening breakdown for a single symbol,
    used by the detail modal when a user clicks a passing ticker."""
    symbol = symbol.strip().upper()
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400
    payload = build_detail_payload(symbol)
    return jsonify(payload)


@app.route("/api/screen", methods=["POST"])
def api_screen():
    data = request.get_json(force=True)
    symbols = data.get("symbols", [])
    symbols = [s.strip().upper() for s in symbols if s.strip()]
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    if len(symbols) > 600:
        return jsonify({"error": "Limit 600 symbols per scan to keep this responsive"}), 400

    all_results = [screen_symbol(s) for s in symbols]
    filtered = _filter_to_passing(all_results)
    return jsonify({
        "results": filtered,
        "scanned_at": datetime.now().isoformat(),
        "total_screened": len(all_results),
        "total_shown": len(filtered),
    })


@app.route("/api/sp500", methods=["GET"])
def api_sp500_list():
    """Returns the S&P 500 ticker list the frontend will scan, plus whether
    it came from a live GitHub fetch or the baked-in snapshot fallback."""
    tickers, source = get_sp500_tickers()
    return jsonify({"tickers": tickers, "count": len(tickers), "source": source})


@app.route("/api/screen-sp500", methods=["POST"])
def api_screen_sp500():
    """Screens the full S&P 500 automatically - no tickers required from
    the user. This is slow (one or two network calls per symbol against
    Yahoo Finance), so it streams progress is not implemented here; the
    frontend should show a long-running spinner and expect this to take
    several minutes for ~500 symbols. Only stocks meeting the pass bar
    (Config.MIN_CRITERIA_PASS out of Config.TOTAL_CRITERIA) are returned."""
    tickers, source = get_sp500_tickers()
    all_results = [screen_symbol(s) for s in tickers]
    filtered = _filter_to_passing(all_results)
    return jsonify({
        "results": filtered,
        "scanned_at": datetime.now().isoformat(),
        "universe_source": source,
        "universe_count": len(tickers),
        "total_screened": len(all_results),
        "total_shown": len(filtered),
    })


if __name__ == "__main__":
    if yf is None:
        print("WARNING: yfinance is not installed. Run: pip install yfinance")
    app.run(debug=True, port=5000)
