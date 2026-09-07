"""Cloud-only market-close draft generator. No credentials or paid APIs."""
import argparse
import json
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal
import yfinance as yf
from PIL import Image, ImageDraw, ImageFont

DISCLAIMER = "Not financial advice. For educational purposes only."
INDEXES = {"S&P 500": "^GSPC", "Nasdaq Composite": "^IXIC", "Dow Jones": "^DJI"}
WATCHLIST = "AAPL MSFT NVDA AMZN META TSLA GOOGL JPM XOM AVGO AMD NFLX".split()
OUT = Path("market_posts")
BG, WHITE, MUTED = "#0B1324", "#F5F7FC", "#AAB8CF"
GREEN, RED, GOLD = "#50E3B5", "#FF7D88", "#F5C96B"


def change(close, previous):
    if not all(math.isfinite(v) and v > 0 for v in (close, previous)):
        raise ValueError("Prices must be finite and positive")
    return (close - previous) / previous * 100


def get_quote(symbol, target):
    h = yf.Ticker(symbol).history(start=str(target - timedelta(days=14)),
                                 end=str(target + timedelta(days=1)), auto_adjust=False)
    if len(h) < 2 or h.index[-1].date() != target:
        raise ValueError(f"Missing or stale close for {symbol}: expected {target}")
    close, previous = float(h.Close.iloc[-1]), float(h.Close.iloc[-2])
    return dict(ticker=symbol, session=str(target), close=close, previous_close=previous,
                change_pct=change(close, previous), source=f"https://finance.yahoo.com/quote/{symbol}/history/")


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" + name, size)


def wrapped(draw, text, xy, size=30, color=WHITE, width=920):
    x, y = xy
    f = font(size)
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            trial = (line + " " + word).strip()
            if draw.textlength(trial, font=f) > width and line:
                draw.text((x, y), line, font=f, fill=color)
                y += size + 14
                line = word
            else:
                line = trial
        draw.text((x, y), line, font=f, fill=color)
        y += size + 20
    if y > (1280 if xy[1] >= 1180 else 1160):
        raise ValueError("Slide text exceeds safe layout area")
    return y


def render(slides, target):
    assets = OUT / "instagram"
    assets.mkdir(parents=True, exist_ok=True)
    images = []
    for i, s in enumerate(slides, 1):
        im = Image.new("RGB", (1080, 1350), BG)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((70, 60, 1010, 110), radius=20, fill="#1B2941")
        d.text((90, 70), f"MARKET CLOSE  /  {target}", font=font(20, True), fill=MUTED)
        wrapped(d, s["title"], (80, 165), 52)
        y = 350
        for label, metric, pct in s["rows"]:
            d.text((80, y), label, font=font(29), fill=MUTED)
            d.text((80, y + 50), metric, font=font(56, True), fill=GREEN if pct >= 0 else RED)
            bar = min(650, max(8, abs(pct) * 70))
            d.rounded_rectangle((80, y + 127, 80 + bar, y + 137), radius=4,
                                fill=GREEN if pct >= 0 else RED)
            y += 185
        wrapped(d, s["body"], (80, max(y + 30, 400)), 27, MUTED)
        d.line((80, 1180, 1000, 1180), fill="#34445F", width=2)
        wrapped(d, DISCLAIMER, (80, 1210), 21, MUTED)
        d.text((80, 1290), "YAHOO FINANCE  |  DAILY CLOSE", font=font(18), fill=GOLD)
        d.text((930, 1290), f"{i} / 6", font=font(18), fill=GOLD)
        path = assets / f"slide_{i:02d}.png"
        im.save(path)
        images.append(im)
    sheet = Image.new("RGB", (810, 675), BG)
    for n, im in enumerate(images):
        sheet.paste(im.resize((270, 337)), ((n % 3) * 270, (n // 3) * 337))
    sheet.save(OUT / "preview.jpg")


def build(data):
    quotes = data["indexes"]
    short = ["S&P 500", "Nasdaq", "Dow"]
    lines = [f"{name}: {q['close']:,.2f} ({q['change_pct']:+.2f}%)" for name, q in quotes.items()]
    x = str(data["session"]) + " close\n" + " | ".join(
        f"{n} {q['change_pct']:+.2f}%" for n, q in zip(short, quotes.values())) + "\n" + DISCLAIMER
    assert len(x) <= 280 and x.isascii()
    up = sum(q["change_pct"] > 0 for q in quotes.values())
    headline = "All three indexes advanced" if up == 3 else "Mixed index performance"
    if all(q["change_pct"] < 0 for q in quotes.values()):
        headline = "All three indexes declined"
    ordered = sorted(data["watchlist"], key=lambda q: q["change_pct"], reverse=True)
    gains = [q for q in ordered if q["change_pct"] > 0][:3]
    losses = [q for q in reversed(ordered) if q["change_pct"] < 0][:3]
    movers = lambda qs: ", ".join(f"{q['ticker']} {q['change_pct']:+.2f}%" for q in qs) or "None"
    body = (f"Market close | {data['session']}\n\n{headline}.\n" + "\n".join(lines)
            + f"\n\nWatchlist gainers: {movers(gains)}.\nWatchlist losers: {movers(losses)}."
            + "\nMovers are from our 12-stock watchlist, not the entire market."
            + "\nThese figures describe price movements; they do not establish their causes."
            + "\nSource: Yahoo Finance daily closing data.\n\n" + DISCLAIMER)
    slides = [dict(title=headline, rows=[(n, f"{q['change_pct']:+.2f}%", q['change_pct'])
              for n, q in quotes.items()], body="Daily change versus the previous trading close.")]
    for name, q in quotes.items():
        slides.append(dict(title=name, rows=[("Closing level", f"{q['close']:,.2f}", q['change_pct']),
                     ("Daily change", f"{q['change_pct']:+.2f}%", q['change_pct'])],
                     body=f"Previous close: {q['previous_close']:,.2f}.\nIndex points, not an ETF share price."))
    slides.append(dict(title="Watchlist movers", rows=[], body="TOP GAINERS\n" + movers(gains)
                  + "\n\nTOP LOSERS\n" + movers(losses)
                  + "\n\nUniverse: " + ", ".join(WATCHLIST)
                  + ". These rankings cover only this watchlist."))
    slides.append(dict(title="What to take away", rows=[], body=headline + ".\n\n"
                  + "Compare all three indexes before drawing conclusions from a single benchmark."
                  + "\n\nPrice changes alone cannot explain why the market moved."
                  + "\n\nSource: Yahoo Finance historical daily bars. Session: " + data['session']
                  + ".\n\nSave this snapshot for your market journal."))
    return dict(status="draft", session=data['session'], x=x,
                linkedin=body + "\n#StockMarket #MarketUpdate",
                instagram_caption=body + "\n#MarketRecap #StockMarket #InvestingEducation",
                slides=slides, watchlist_gainers=gains, watchlist_losers=losses)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert abs(change(110, 100) - 10) < 1e-10
        assert abs(change(90, 100) + 10) < 1e-10
        for bad in (0, float("nan")):
            try:
                change(bad, 100)
                raise AssertionError("Invalid price accepted")
            except ValueError:
                pass
        print("Calculation tests passed")
        return
    now = datetime.now(ZoneInfo("America/New_York"))
    target = date.fromisoformat(args.date) if args.date else now.date()
    calendar = mcal.get_calendar("NYSE").schedule(start_date=target, end_date=target)
    OUT.mkdir(exist_ok=True)
    if calendar.empty:
        (OUT / "status.json").write_text(json.dumps(dict(status="skipped", reason="Market holiday or weekend", session=str(target))))
        print("No trading session; skipped")
        return
    close_time = calendar.iloc[0].market_close.to_pydatetime()
    if now < close_time + timedelta(minutes=30):
        raise ValueError("Requested session is not yet closed or data is still settling")
    data = dict(session=str(target), fetched_at=now.isoformat(), source="Yahoo Finance via yfinance",
                indexes={n: get_quote(t, target) for n, t in INDEXES.items()},
                watchlist=[get_quote(t, target) for t in WATCHLIST])
    (OUT / "raw_market_data.json").write_text(json.dumps(data, indent=2))
    for q in list(data['indexes'].values()) + data['watchlist']:
        expected = (q['close'] / q['previous_close'] - 1) * 100
        assert abs(expected - q['change_pct']) < 1e-8
    package = build(data)
    assert len(package['slides']) == 6
    for key in ('x', 'linkedin', 'instagram_caption'):
        assert DISCLAIMER in package[key]
        (OUT / (key + '.txt')).write_text(package[key], encoding='utf-8')
    render(package['slides'], target)
    package['instagram_assets'] = [f"instagram/slide_{i:02d}.png" for i in range(1, 7)]
    (OUT / "today.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    (OUT / "validation_report.json").write_text(json.dumps(dict(valid=True, session=str(target),
        checks=["session freshness", "finite positive prices", "recomputed percentages", "X length", "disclaimers", "six slides", "layout bounds"],
        limitation="Single-provider validation; not independent source verification."), indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("## Drafts generated for " + str(target) + "\n\n" + package['linkedin'])
    print("Draft package generated:", target)


if __name__ == "__main__":
    main()
