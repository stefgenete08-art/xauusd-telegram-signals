"""
Scheduled XAU/USD Telegram signal scanner.
Runs once per GitHub Actions invocation; does not place trades.
"""
import os
from pathlib import Path
import logging
import requests
import pandas as pd

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_KEY = os.environ["TWELVEDATA_API_KEY"]
SYMBOL = os.getenv("SYMBOL", "XAU/USD")
STATE_FILE = Path(".state/last_alert.txt")
TD_URL = "https://api.twelvedata.com/time_series"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("xauusd")


def candles(interval, count=160):
    r = requests.get(TD_URL, params={
        "symbol": SYMBOL, "interval": interval, "outputsize": count,
        "timezone": "UTC", "apikey": API_KEY
    }, timeout=25)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise RuntimeError(f"Market data error: {data.get('message', data)}")
    df = pd.DataFrame(data["values"])
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.dropna().sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    # Ignore the currently-forming candle.
    if len(df) > 1:
        df = df.iloc[:-1].copy()
    if len(df) < 60:
        raise RuntimeError(f"Insufficient {interval} candles: {len(df)}")
    return df


def indicators(df):
    x = df.copy()
    x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
    x["ema50"] = x.close.ewm(span=50, adjust=False).mean()
    delta = x.close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = losses.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    x["rsi"] = (100 - 100 / (1 + rs)).fillna(50)
    macd = x.close.ewm(span=12, adjust=False).mean() - x.close.ewm(span=26, adjust=False).mean()
    x["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    prev = x.close.shift(1)
    tr = pd.concat([(x.high-x.low), (x.high-prev).abs(), (x.low-prev).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    return x.dropna().reset_index(drop=True)


def analyse():
    m5 = indicators(candles("5min"))
    m15 = indicators(candles("15min"))
    a, b = m5.iloc[-1], m15.iloc[-1]

    buy = a.ema20 > a.ema50 and a.macd_hist > 0 and 52 <= a.rsi <= 68 and b.ema20 > b.ema50
    sell = a.ema20 < a.ema50 and a.macd_hist < 0 and 32 <= a.rsi <= 48 and b.ema20 < b.ema50
    side = "BUY" if buy else "SELL" if sell else "WAIT"

    price, atr = float(a.close), float(a.atr)
    if side == "BUY":
        sl, tp1, tp2 = price - 1.5*atr, price + 1.5*atr, price + 2*atr
        reason = "5m bullish EMA/momentum and 15m bullish trend agree."
    elif side == "SELL":
        sl, tp1, tp2 = price + 1.5*atr, price - 1.5*atr, price - 2*atr
        reason = "5m bearish EMA/momentum and 15m bearish trend agree."
    else:
        sl = tp1 = tp2 = None
        reason = "Timeframes or momentum do not align; no setup."
    stamp = a.datetime.strftime("%Y-%m-%d %H:%M UTC")
    return side, stamp, price, sl, tp1, tp2, float(a.rsi), reason


def send(text):
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")


def main():
    side, stamp, price, sl, tp1, tp2, rsi, reason = analyse()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    previous = STATE_FILE.read_text().strip() if STATE_FILE.exists() else "WAIT"

    # Only alert on a change of state, avoiding repeated BUY/SELL messages
    # on every scheduled run while the same setup remains active.
    if side == previous:
        log.info("No signal-state change (%s); no Telegram message.", side)
        return

    if side == "WAIT":
        if previous in ("BUY", "SELL"):
            message = (
                f"XAU/USD — EXIT / REVIEW WARNING\n"
                f"Previous setup: {previous}\n"
                f"Last closed 5m candle: {stamp}\n"
                f"Reference price: {price:.2f}\n"
                f"Momentum/timeframe confirmation no longer supports the setup.\n"
                "Review your position and broker-side stop. This bot cannot see or close your trade."
            )
            send(message)
        STATE_FILE.write_text("WAIT")
        log.info("State changed to WAIT.")
        return

    message = (
        f"XAU/USD — {side} SETUP (analysis only)\n"
        f"Last closed 5m candle: {stamp}\n"
        f"Reference entry: {price:.2f}\n"
        f"Stop-loss estimate: {sl:.2f}\n"
        f"Take-profit 1: {tp1:.2f}\n"
        f"Take-profit 2: {tp2:.2f}\n"
        f"RSI(14): {rsi:.1f}\n"
        f"Reason: {reason}\n"
        "Confirm your broker's live quote, spread and candle before acting. "
        "These are estimates, not executable prices."
    )
    if previous in ("BUY", "SELL") and previous != side:
        message = (
            f"Opposite signal to previous {previous} setup. Review/close any existing "
            f"position according to your own plan.\n\n" + message
        )
    send(message)
    STATE_FILE.write_text(side)
    log.info("Sent %s signal.", side)

if __name__ == "__main__":
    main()
