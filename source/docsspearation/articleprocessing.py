import os
import json
import re
import requests
import logging
from pathlib import Path
from bs4 import BeautifulSoup

# ─── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

# ─── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR  = BASE_DIR / "source"/"news_articles"
DST_DIR  = BASE_DIR / "chunks" / "news_articles"
DST_DIR.mkdir(parents=True, exist_ok=True)

# ─── Helpers ───────────────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    paras = re.split(r'\n{2,}', text)
    clean = []
    for p in paras:
        p2 = re.sub(r'\s+', ' ', p).strip()
        if p2:
            clean.append(p2)
    return "\n\n".join(clean)

def fetch_full_text(url: str) -> (str, str):
    """
    Try a cascade of CSS selectors (deepest first) to extract paragraphs.
    Returns (body_text, selector_used).
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Deeper-first list of selectors
        selectors = [
            # exact chain under main > page-wrapper > page-article > article-content...
            "main#main div.page-wrapper div.page-article div.article-content "
            "div.field.field-body div[itemprop='articleBody']",

            # as before: itemprop + dable-content-wrapper
            "div[itemprop='articleBody'].dable-content-wrapper",

            # less specific chains
            "div.article-content div.field.field-body div[itemprop='articleBody']",
            "div.article-content div.field.field-body",
            ".entry-content",
            ".article-content",
        ]

        for sel in selectors:
            container = soup.select_one(sel)
            if container:
                paras = container.find_all("p")
                if paras:
                    raw = "\n\n".join(p.get_text() for p in paras)
                    return clean_text(raw), sel

        # fallback: all <p>
        paras = soup.find_all("p")
        raw = "\n\n".join(p.get_text() for p in paras)
        return clean_text(raw), "<all p>"

    except Exception as e:
        logging.debug(f"Error fetching {url}: {e}")
        return "", "error"

# ─── Main loop ─────────────────────────────────────────────────────────────────
failures = []
for path in sorted(SRC_DIR.glob("article_*.json")):
    art       = json.loads(path.read_text(encoding="utf-8"))
    art_id    = art["id"]
    title     = art["title"].strip()
    published = art["published"].strip()
    url       = art["link"].strip()

    body, used_sel = fetch_full_text(url)
    if not body:
        logging.error(f"[FAIL] ID {art_id}: no content ({url})")
        failures.append(art_id)
    else:
        logging.info(f"[OK]   ID {art_id}: selector `{used_sel}`")

    # Write the .txt (even if empty, for inspection)
    out_path = DST_DIR / f"news_{art_id:03d}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# source: news_articles\n")
        f.write(f"# id: {art_id}\n")
        f.write(f"# title: {title}\n")
        f.write(f"# published: {published}\n")
        f.write(f"# url: {url}\n\n")
        f.write(body + "\n")

if failures:
    logging.info(f"\nTotal failures: {len(failures)} articles\n"
                 + ", ".join(str(i) for i in failures))
else:
    logging.info("All articles fetched successfully.")









