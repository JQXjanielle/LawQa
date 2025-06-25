import os
import json
import urllib.parse

import feedparser
import requests
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder  # optional, if you’re still unwrapping redirects

# ─── Helpers ────────────────────────────────────────────────────────────────────
def extract_real_url(url: str) -> str:
    # 1) Try Atom <link rel="alternate">
    # 2) Fallback to feed.link
    # 3) If still Google-News, use gnewsdecoder or meta-refresh
    try:
        # if it's still a news.google.com URL, decode it
        if "news.google.com" in url:
            dec = gnewsdecoder(url, interval=1)
            if dec.get("status"):
                return dec["decoded_url"]
    except Exception:
        pass
    return url

# ─── Build & parse RSS ──────────────────────────────────────────────────────────
TERMS   = "kesalahan memandu OR pelanggaran jalan raya OR memandu laju"
qs      = urllib.parse.quote(TERMS)
RSS_URL = f"https://news.google.com/rss/search?q={qs}&hl=ms&gl=MY&ceid=MY:ms"

feed    = feedparser.parse(RSS_URL)
entries = feed.entries[:100]

# ─── Write JSON files ───────────────────────────────────────────────────────────
OUT = "source/news_articles"
os.makedirs(OUT, exist_ok=True)

master_index = []
for i, e in enumerate(entries, start=1):
    # pick the Atom-side “alternate” if present
    real_link = None
    for L in getattr(e, "links", []):
        if L.get("rel") == "alternate":
            real_link = L["href"]
            break

    chosen = real_link or e.link
    chosen = extract_real_url(chosen)

    rec = {
        "id":        i,
        "title":     e.title,
        "published": e.published,
        "link":      chosen
    }

    with open(f"{OUT}/article_{i:03d}.json", "w", encoding="utf-8") as fp:
        json.dump(rec, fp, ensure_ascii=False, indent=2)

    master_index.append(rec)

with open(f"{OUT}/index.json", "w", encoding="utf-8") as fp:
    json.dump(master_index, fp, ensure_ascii=False, indent=2)

print(f"✅ Fetched {len(entries)} articles into `{OUT}/` (no more summaries!)")







