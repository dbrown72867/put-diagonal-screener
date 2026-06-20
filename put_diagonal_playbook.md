# Put Diagonal Calendar Spread — Entry, Roll & Risk Checklist

**Strategy type:** Long-biased put diagonal ("poor man's put" structure)
**Long leg:** 30–45 DTE put, 40–60 delta (deep ITM)
**Short leg:** weekly put (Friday expiry), 20–30 delta, rolled every Friday
**Bias:** profits from slow downward drift / sideways-to-down price action, IV elevated and contracting on the short leg, net positive theta

---

## 1. Underlying Screen (run before entry, and weekly before each roll)

All of the following should be true. Treat this as a checklist, not a scoring system — a name that fails 2+ filters is a pass, not a "lower conviction buy."

| # | Criterion | Rule | Why it's here |
|---|-----------|------|----------------|
| 1 | **RSI** | Oversold (typically RSI(14) < 30) | Entry timing signal — looking for a stretched/bounce setup |
| 2 | **Trend filter** | Price/SMA above the 50-day SMA | Confirms the longer-term trend is still up despite the short-term oversold reading — you're buying a dip in an uptrend, not catching a falling knife |
| 3 | **Bollinger Bands** | Price has previously bounced off the lower band (pattern check, not current touch) | Confirms the lower band has acted as support historically for this name |
| 4 | **Implied Volatility (IV)** | IV > 50 (IV Rank or IV itself — specify which you mean and keep it consistent) | High IV = rich premium to sell on the short leg |
| 5 | **Vol term structure** | Short-term IV > long-term IV (backwardation) | Front-month vol is relatively rich vs. back-month — favorable for selling the near leg vs. buying the far leg. Note: this is a less common term structure (usually seen around earnings/events) — confirm there isn't a scheduled catalyst that will invalidate the trade right after entry |
| 6 | **Liquidity (underlying)** | Average daily volume > 1,000,000 shares | Ensures the name itself is liquid enough to trade in size without excess slippage |
| 7 | **Liquidity (options)** | Tight bid/ask spread on the specific contracts (define a hard number, e.g. ≤ $0.10 or ≤ 5% of mid) | Wide option spreads erode edge on every roll, since you're transacting weekly |

---

## 2. Strike & Structure Rules (entry)

| Parameter | Rule |
|---|---|
| Long leg expiration | 30–45 DTE |
| Long leg delta | 40–60 delta put |
| Short leg expiration | Current week, expiring Friday |
| Short leg delta | 20–30 delta put |
| Strike width (long strike − short strike) | ≤ $7.00 |
| Position theta | Net positive (short leg theta must outweigh long leg theta decay) |
| Short strike delta tolerance band (post-entry, pre-roll) | 0.20–0.35 — this is your monitoring band between Fridays, wider than the 0.20–0.30 entry filter to avoid over-trading on small moves |
| Spread cost vs. total premium | Net debit paid for the diagonal should be 10–15% of [define basis — see note below] |

> **Note on rule #6 above ("10–15% of total premium"):** this needs one clarification before it's codeable — 10–15% of *what*? Common interpretations:
> - 10–15% of the **long put's premium** (i.e., the short leg should collect at least 10–15% of what you paid for the long leg, each cycle)
> - 10–15% of the **strike width** (i.e., net debit ≤ 10–15% of the $7 max width, so ≤ ~$0.70–$1.05 net debit)
> - 10–15% of the **underlying's share price**
>
> Pick one and I'll bake it into the rule set — flagged as TBD below.

---

## 3. Weekly Roll Rules (every Friday)

1. **Close** the current week's short put (buy to close), ideally same-day or at market close Friday.
2. **Re-screen** the underlying against Section 1 criteria. If it now fails 2+ filters, this is a signal to exit the whole diagonal rather than continue rolling — don't roll mechanically into a broken setup.
3. **Open** the new short put for the following Friday's expiration, at 20–30 delta.
4. **Re-check** strike width: new short strike to existing long strike must still be ≤ $7. If the underlying has moved enough that no strike in the 20-30 delta band keeps you under $7 wide, you have two choices to decide on in advance:
   - Roll the long leg out/down too (full diagonal reset), or
   - Skip the roll that week and hold the long leg naked until strikes realign
5. **Re-verify** net position theta is still positive after the roll.
6. **Log** the roll: strikes, deltas, IV at entry, credit/debit collected, and DTE remaining on the long leg.

---

## 4. Long Leg Management

- When the long leg drops under ~20–25 DTE, it stops being a good "anchor" (delta becomes unstable, theta decay on it accelerates) — decide in advance whether your rule is to roll it forward at that point or close the whole structure.
- Track total credits collected from short-leg rolls against the long leg's cost basis — this tells you your real breakeven and how much of the long leg's premium has been "paid for" by short-leg theta.

---

## 5. Exit Triggers (define before entry, not during)

Things worth deciding now, in writing, so you're not deciding emotionally on a Friday:
- Underlying breaks below the lower Bollinger Band decisively (invalidates the "bounce off support" thesis) → exit or defend?
- Underlying rips through the long put's strike (max profit zone) → take profit on the whole structure or keep rolling shorts?
- IV collapses below your entry threshold → stop rolling, since the "rich premium" edge is gone?
- Long leg approaching expiration with no good roll available?

---

## 6. Open Items to Finalize Before Automating

1. **IV(>50)** — IV itself, or IV Rank/Percentile? These behave very differently across stocks.
2. **"10–15% of total premium"** — basis needs picking (see Section 2 note).
3. **Bid/ask "tight"** — needs a hard number (absolute $ or % of mid) to be screenable.
4. **Bollinger "bounce off lower band previously"** — needs a lookback window (e.g., touched/closed below lower band and recovered within last 10/20 trading days) and a definition of "bounce" (close back above the band? above the 20-day SMA?).
5. **RSI period and oversold threshold** — confirm RSI(14) < 30, or a different period/threshold.
6. **SMA period for "above the 50-day SMA"** — confirm you mean *price* above the 50-day SMA (not a faster SMA crossing above it).
