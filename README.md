# Market social agent

Private cloud workflow generating market-close drafts for X, LinkedIn and a six-image Instagram carousel. No API keys, paid models, local service, or publishing credentials.

## Use

Open **Actions > Market social drafts > Run workflow**. Leave the date blank for today, or enter a completed trading session such as 2026-09-04. Open the completed run and download its artifact. Files expire after five days.

Outputs include today.json, raw_market_data.json, validation_report.json, three caption text files, six 1080x1350 PNG slides, and preview.jpg. Review before manually posting.

## Schedule

Two weekday UTC triggers cover daylight and standard time. A timezone gate permits only the trigger corresponding to 4:30 PM America/New_York. GitHub may delay scheduled runs; this is not an exact-time service. Market holidays/weekends produce a skip report. Early-close sessions still run at 4:30 PM. Incomplete or stale market data fails the run.

## Scope and accuracy

S&P 500, Nasdaq Composite and Dow Jones are actual index levels, not SPY/QQQ/DIA ETF prices. Gainers and losers are explicitly limited to AAPL, MSFT, NVDA, AMZN, META, TSLA, GOOGL, JPM, XOM, AVGO, AMD and NFLX. This is not a full-market ranking.

Content uses deterministic templates. Prices are checked for validity and session date; changes are recalculated independently from the same fetched data. This does not cross-check another provider. Headlines never invent economic causes. Every caption and slide has the requested educational disclaimer.

Yahoo/yfinance can rate-limit requests or omit data. The free data connection is suitable for a draft prototype; access does not grant redistribution rights. Review Yahoo/provider terms before public or commercial distribution. No claim of licensed real-time data is made.

## Cost controls

Uses standard Ubuntu GitHub runners, ten-minute job timeouts, and five-day artifact retention. No paid API or external hosting. Private Actions usage and storage share the account's free quota with other repositories, so zero cost depends on staying within that quota and the account's billing settings. This project does not enable paid usage or change billing settings.

## Failure recovery

Inspect the failed Actions step. For a temporary data error, manually rerun for the same date later. Failed runs must not be treated as publishable drafts. There is no publishing adapter and reruns cannot create duplicate social posts.

## Implementation

agent.py contains fetching, numerical checks, template copy, image rendering and calculation self-tests. .github/workflows/market-social.yml installs dependencies and runs everything in GitHub. No local installation is required.
