# XAU/USD Telegram Signals — GitHub Actions

This is an alert-only educational scanner. It does not place or manage trades.

## Files
- `bot.py`: fetches completed 5m and 15m candles, calculates EMA20/50, RSI, MACD histogram and ATR, then sends a BUY/SELL alert only when the signal state changes; it sends an exit/review warning when an active setup returns to WAIT.
- `.github/workflows/scan.yml`: runs on a five-minute GitHub Actions schedule and can also be run manually.
- `requirements.txt`: Python dependencies.

## Setup on a phone
1. Create a **public** GitHub repository (public repositories get standard GitHub-hosted runners at no charge within GitHub's applicable limits).
2. Upload the extracted files and folders, preserving `.github/workflows/scan.yml`.
3. In the repository open Settings → Secrets and variables → Actions → New repository secret.
4. Add these secrets exactly:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `TWELVEDATA_API_KEY`
5. In Telegram, open your bot and send `/start`. Obtain your numeric chat ID using a trusted method such as the `@userinfobot` Telegram bot. Do not publish your bot token.
6. In GitHub, open Actions → XAUUSD Telegram signals → Run workflow.
7. Check the run log. If successful, wait for scheduled runs and check Telegram.

## Important
- Scheduled workflows can be delayed and are not guaranteed to execute exactly every five minutes. GitHub may throttle or skip schedules during high load. They are not a tick-by-tick alert service.
- The free standard runner allowance and policy can change. Public repositories are the safest way to avoid consuming private-repository included minutes, but review GitHub's current terms.
- The Twelve Data plan must support XAU/USD and 5m/15m intraday candles; provider quotas may limit repeated requests.
- GitHub Actions cache stores the last signal state to reduce repeat alerts. Cache restoration is best-effort, not a guaranteed trading ledger.
- Market data may differ from your broker's quote, spread and candle boundaries.
- BUY/SELL labels are rule-based technical signals, not forecasts or recommendations. ATR levels are illustrative, not tested or guaranteed. Use a demo account only until independently backtested.
- Never store tokens or API keys in source files, screenshots, commits or public issues. Store them only as repository Actions secrets.
