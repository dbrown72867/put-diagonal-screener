"""
Put Diagonal Calendar Spread — Scanner & Roll Logic Outline
=============================================================

This is a STRUCTURE/SKELETON, not a finished trading system. It shows how each
of your stated criteria maps to a function and a data dependency. Several
thresholds are marked TBD — see put_diagonal_playbook.md Section 6 for the
open questions that need answers before this can run against real data.

This script does NOT execute trades. It screens and reports candidates. Wiring
it to a broker API for actual order placement is a separate, much more
consequential step that should only happen after you've paper-traded the logic.

Data dependencies you'll need to supply (not included here):
  - Daily OHLCV history (for RSI, SMA, Bollinger Bands)
  - Option chain snapshots with greeks (delta, theta), IV, bid/ask, OI/volume
  - A term-structure source (front-month IV vs. back-month IV, e.g. 30d vs 60-90d)

Common sources: a broker API (TastyTrade, IBKR, Tradier), or a market data
vendor (ORATS, CBOE DataShop, Polygon.io). None are wired up here.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Config — your stated rules, with TBD thresholds flagged explicitly
# ---------------------------------------------------------------------------

class Config:
    # Underlying screen
    RSI_PERIOD = 14
    RSI_OVERSOLD_MAX = 30          # TBD: confirm threshold

    SMA_TREND_PERIOD = 50          # price must be above this SMA

    BOLLINGER_PERIOD = 20
    BOLLINGER_STD = 2
    BOLLINGER_BOUNCE_LOOKBACK_DAYS = 20   # TBD: confirm lookback window for "previously bounced"

    IV_MIN = 50.0                  # TBD: confirm this is IV itself vs IV Rank/Percentile
    IV_IS_RANK = False             # set True if IV_MIN should be interpreted as IV Rank (0-100)

    MIN_AVG_DAILY_VOLUME = 1_000_000

    MAX_BID_ASK_SPREAD_PCT = 0.05  # TBD: confirm — 5% of mid used as placeholder for "tight"
    MAX_BID_ASK_SPREAD_ABS = None  # alternative: set a flat dollar cap instead, e.g. 0.10

    # Option structure
    LONG_DTE_MIN = 30
    LONG_DTE_MAX = 45
    LONG_DELTA_MIN = 0.40
    LONG_DELTA_MAX = 0.60

    SHORT_DELTA_ENTRY_MIN = 0.20
    SHORT_DELTA_ENTRY_MAX = 0.30

    SHORT_DELTA_MONITOR_MIN = 0.20  # wider monitoring band between rolls
    SHORT_DELTA_MONITOR_MAX = 0.35

    MAX_STRIKE_WIDTH = 7.00

    # TBD: basis for "10-15% of total premium" — see playbook Section 2.
    # Placeholder implementation assumes basis = long put premium.
    NET_DEBIT_MIN_PCT_OF_LONG_PREMIUM = 0.10
    NET_DEBIT_MAX_PCT_OF_LONG_PREMIUM = 0.15

    LONG_LEG_ROLL_DTE_TRIGGER = 21  # roll/reassess long leg under this DTE


# ---------------------------------------------------------------------------
# Data shapes (replace with real data classes / API response models)
# ---------------------------------------------------------------------------

@dataclass
class PriceBar:
    dt: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class OptionQuote:
    expiry: date
    strike: float
    delta: float        # negative for puts in some conventions — normalize to positive magnitude here
    theta: float
    iv: float
    bid: float
    ask: float
    open_interest: int
    volume: int

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / self.mid if self.mid else float("inf")

    @property
    def dte(self) -> int:
        return (self.expiry - date.today()).days


# ---------------------------------------------------------------------------
# Indicator calculations
# ---------------------------------------------------------------------------

def compute_rsi(bars: list[PriceBar], period: int = 14) -> float:
    """Standard Wilder RSI on closing prices. Returns latest RSI value."""
    closes = [b.close for b in bars]
    if len(closes) < period + 1:
        raise ValueError("Not enough bars for RSI")
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
    return 100 - (100 / (1 + rs))


def compute_sma(bars: list[PriceBar], period: int) -> float:
    closes = [b.close for b in bars[-period:]]
    return sum(closes) / len(closes)


def compute_bollinger_bands(bars: list[PriceBar], period: int = 20, num_std: float = 2):
    """Returns (lower_band, middle_sma, upper_band) for the latest bar."""
    closes = [b.close for b in bars[-period:]]
    sma = sum(closes) / len(closes)
    variance = sum((c - sma) ** 2 for c in closes) / len(closes)
    std = variance ** 0.5
    return sma - num_std * std, sma, sma + num_std * std


def has_bounced_off_lower_band(bars: list[PriceBar], lookback_days: int) -> bool:
    """
    Checks whether price touched/closed below the lower band at some point in
    the lookback window AND recovered back above the band by a later bar.

    NOTE: "bounce" definition is a placeholder (close back above lower band).
    Confirm whether you want a stricter bounce definition (e.g. close back
    above the 20-day SMA, or a minimum % recovery).
    """
    window = bars[-lookback_days:]
    touched_low = False
    for i, b in enumerate(window):
        sub_history = bars[: bars.index(b) + 1]
        if len(sub_history) < 20:
            continue
        lower, _, _ = compute_bollinger_bands(sub_history)
        if b.close <= lower:
            touched_low = True
        elif touched_low and b.close > lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Underlying screen
# ---------------------------------------------------------------------------

@dataclass
class ScreenResult:
    symbol: str
    passed: bool
    detail: dict


def screen_underlying(
    symbol: str,
    bars: list[PriceBar],
    iv_current: float,
    iv_short_term: float,
    iv_long_term: float,
    avg_daily_volume: float,
    cfg: Config = Config(),
) -> ScreenResult:
    checks = {}

    rsi = compute_rsi(bars, cfg.RSI_PERIOD)
    checks["rsi_oversold"] = rsi < cfg.RSI_OVERSOLD_MAX

    sma50 = compute_sma(bars, cfg.SMA_TREND_PERIOD)
    checks["above_50sma"] = bars[-1].close > sma50

    checks["bollinger_bounce_history"] = has_bounced_off_lower_band(
        bars, cfg.BOLLINGER_BOUNCE_LOOKBACK_DAYS
    )

    checks["iv_above_threshold"] = iv_current > cfg.IV_MIN

    checks["term_structure_backwardation"] = iv_short_term > iv_long_term

    checks["volume_above_min"] = avg_daily_volume > cfg.MIN_AVG_DAILY_VOLUME

    passed = all(checks.values())
    return ScreenResult(symbol=symbol, passed=passed, detail={"rsi": rsi, "sma50": sma50, **checks})


# ---------------------------------------------------------------------------
# Option leg selection
# ---------------------------------------------------------------------------

def select_long_leg(chain: list[OptionQuote], cfg: Config = Config()) -> Optional[OptionQuote]:
    candidates = [
        q for q in chain
        if cfg.LONG_DTE_MIN <= q.dte <= cfg.LONG_DTE_MAX
        and cfg.LONG_DELTA_MIN <= abs(q.delta) <= cfg.LONG_DELTA_MAX
        and q.spread_pct <= cfg.MAX_BID_ASK_SPREAD_PCT
    ]
    if not candidates:
        return None
    # pick delta closest to midpoint of band as a reasonable default
    target = (cfg.LONG_DELTA_MIN + cfg.LONG_DELTA_MAX) / 2
    return min(candidates, key=lambda q: abs(abs(q.delta) - target))


def select_short_leg(
    chain: list[OptionQuote],
    long_leg: OptionQuote,
    target_friday: date,
    cfg: Config = Config(),
) -> Optional[OptionQuote]:
    candidates = [
        q for q in chain
        if q.expiry == target_friday
        and cfg.SHORT_DELTA_ENTRY_MIN <= abs(q.delta) <= cfg.SHORT_DELTA_ENTRY_MAX
        and q.spread_pct <= cfg.MAX_BID_ASK_SPREAD_PCT
        and (long_leg.strike - q.strike) <= cfg.MAX_STRIKE_WIDTH
        and q.strike <= long_leg.strike  # short strike below long strike for a put diagonal
    ]
    if not candidates:
        return None
    target = (cfg.SHORT_DELTA_ENTRY_MIN + cfg.SHORT_DELTA_ENTRY_MAX) / 2
    return min(candidates, key=lambda q: abs(abs(q.delta) - target))


def net_position_theta(long_leg: OptionQuote, short_leg: OptionQuote) -> float:
    """Long put theta is typically negative (you pay decay); short put theta
    is positive to you (you collect decay). Net should be positive."""
    return short_leg.theta - long_leg.theta  # sign convention: confirm against your data source


def validate_net_debit(
    long_leg: OptionQuote, short_leg: OptionQuote, cfg: Config = Config()
) -> bool:
    """Placeholder basis: % of long put premium. Swap basis per your answer
    to the Section 2 open question in the playbook."""
    net_debit = long_leg.mid - short_leg.mid
    if long_leg.mid == 0:
        return False
    pct = net_debit / long_leg.mid
    return cfg.NET_DEBIT_MIN_PCT_OF_LONG_PREMIUM <= pct <= cfg.NET_DEBIT_MAX_PCT_OF_LONG_PREMIUM


# ---------------------------------------------------------------------------
# Weekly roll logic
# ---------------------------------------------------------------------------

def next_friday(today: date) -> date:
    days_ahead = (4 - today.weekday()) % 7  # Monday=0 ... Friday=4
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


@dataclass
class Position:
    symbol: str
    long_leg: OptionQuote
    short_leg: OptionQuote


def weekly_roll(
    position: Position,
    fresh_chain: list[OptionQuote],
    bars: list[PriceBar],
    iv_current: float,
    iv_short_term: float,
    iv_long_term: float,
    avg_daily_volume: float,
    cfg: Config = Config(),
) -> dict:
    """
    Run every Friday. Returns an action plan — does NOT place trades.
    """
    result = {"symbol": position.symbol, "actions": []}

    # 1. Re-screen the underlying
    screen = screen_underlying(
        position.symbol, bars, iv_current, iv_short_term, iv_long_term, avg_daily_volume, cfg
    )
    if not screen.passed:
        failed = [k for k, v in screen.detail.items() if v is False]
        result["actions"].append(
            f"RE-SCREEN FAILED ({failed}) — consider closing the whole diagonal instead of rolling"
        )
        return result

    # 2. Close current short leg
    result["actions"].append(
        f"BUY TO CLOSE short put {position.short_leg.strike} exp {position.short_leg.expiry}"
    )

    # 3. Check long leg DTE — does it need its own roll first?
    if position.long_leg.dte < cfg.LONG_LEG_ROLL_DTE_TRIGGER:
        result["actions"].append(
            f"LONG LEG DTE {position.long_leg.dte} < {cfg.LONG_LEG_ROLL_DTE_TRIGGER} "
            f"— roll long leg forward before continuing, or close structure"
        )
        return result

    # 4. Select new short leg for next Friday
    target_exp = next_friday(date.today())
    new_short = select_short_leg(fresh_chain, position.long_leg, target_exp, cfg)
    if new_short is None:
        result["actions"].append(
            f"NO VALID SHORT STRIKE within ${cfg.MAX_STRIKE_WIDTH} width and "
            f"{cfg.SHORT_DELTA_ENTRY_MIN}-{cfg.SHORT_DELTA_ENTRY_MAX} delta for {target_exp} "
            f"— decide: roll long leg too, or skip this week's short"
        )
        return result

    # 5. Confirm net theta still positive
    theta = net_position_theta(position.long_leg, new_short)
    if theta <= 0:
        result["actions"].append(
            f"WARNING: net theta {theta:.4f} not positive with proposed short strike "
            f"{new_short.strike} — review before opening"
        )

    result["actions"].append(
        f"SELL TO OPEN short put {new_short.strike} exp {new_short.expiry} "
        f"(delta {new_short.delta:.2f}, theta {new_short.theta:.4f})"
    )
    result["new_short_leg"] = new_short
    result["net_theta"] = theta
    return result


# ---------------------------------------------------------------------------
# Example usage (pseudocode — replace data calls with your actual provider)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # bars = your_data_provider.get_daily_bars("XYZ", lookback=100)
    # chain = your_data_provider.get_option_chain("XYZ")
    # iv_current, iv_short, iv_long = your_data_provider.get_iv_term_structure("XYZ")
    # avg_vol = your_data_provider.get_avg_volume("XYZ", days=20)
    #
    # screen = screen_underlying("XYZ", bars, iv_current, iv_short, iv_long, avg_vol)
    # if screen.passed:
    #     long_leg = select_long_leg(chain)
    #     short_leg = select_short_leg(chain, long_leg, next_friday(date.today()))
    #     if long_leg and short_leg and validate_net_debit(long_leg, short_leg):
    #         print(f"Candidate: long {long_leg.strike}/{long_leg.expiry}, "
    #               f"short {short_leg.strike}/{short_leg.expiry}")
    pass
