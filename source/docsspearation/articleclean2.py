import os
import json
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ─── Constants ─────────────────────────────────────────────────────────────────
FAILED_IDS = [14,75,60,58, 43, 44]
BASE_DIR   = Path(__file__).parent
SRC_DIR    = BASE_DIR / "source"/"news_articles"
DST_DIR    = BASE_DIR / "chunks" / "news_articles"
DST_DIR.mkdir(parents=True, exist_ok=True)

# ─── Helper ────────────────────────────────────────────────────────────────────
def clean_text(text):
    paras = re.split(r'\n{2,}', text)
    cleaned = []
    for p in paras:
        p2 = re.sub(r'\s+', ' ', p).strip()
        if p2:
            cleaned.append(p2)
    return "\n\n".join(cleaned)

# ─── Setup headless Chrome ─────────────────────────────────────────────────────
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# ─── Retry loop ─────────────────────────────────────────────────────────────────
for art_id in FAILED_IDS:
    json_path = SRC_DIR / f"article_{art_id:03d}.json"
    if not json_path.exists():
        print(f"ID {art_id}: JSON missing")
        continue

    art = json.loads(json_path.read_text("utf-8"))
    url = art["link"]
    
    try:
        driver.get(url)
        time.sleep(3)  # wait for JavaScript to execute
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # target container
        container = soup.select_one("div[itemprop='articleBody'].dable-content-wrapper")
        if not container:
            container = soup.select_one("main#main div.page-article")
        
        if container:
            paras = [p.get_text().strip() for p in container.find_all("p") if p.get_text(strip=True)]
            raw = "\n\n".join(paras)
            body = clean_text(raw)
        else:
            # super fallback to all <p>
            ps = soup.find_all("p")
            body = clean_text("\n\n".join(p.get_text() for p in ps))

        if not body:
            print(f"ID {art_id}: still no content extracted.")
        else:
            print(f"ID {art_id}: extracted {len(body)} characters.")

        # write out txt
        out_path = DST_DIR / f"news_{art_id:03d}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# source: news_articles\n# id: {art_id}\n")
            f.write(f"# title: {art['title']}\n# published: {art['published']}\n")
            f.write(f"# url: {url}\n\n")
            f.write(body + "\n")

    except Exception as e:
        print(f"ID {art_id}: Error fetching {url}: {e}")

# ─── Cleanup ───────────────────────────────────────────────────────────────────
driver.quit()



