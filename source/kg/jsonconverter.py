import os
import re
import json
from pathlib import Path
from email.utils import parsedate_to_datetime

# ─── Helpers ────────────────────────────────────────────────────────────────────
def parse_metadata(text: str) -> dict:
    """
    Parse leading lines starting with '#' into key:value pairs,
    supporting multi-line continuations.
    """
    meta = {}
    last_key = None
    for line in text.splitlines():
        if not line.strip():
            break
        if line.startswith('#'):
            inner = line[1:].strip()
            if ':' in inner:
                key, val = inner.split(':', 1)
                key = key.strip().lower()
                val = val.strip()
                meta[key] = val
                last_key = key
            else:
                if last_key:
                    meta[last_key] += ' ' + inner
        else:
            if last_key:
                meta[last_key] += ' ' + line.strip()
    return meta

def normalize_published(pub: str) -> str:
    """
    Convert RFC-822 dates (e.g. 'Tue, 17 Jun 2025 03:23:00 GMT')
    to ISO 8601 (e.g. '2025-06-17T03:23:00Z').
    """
    try:
        dt = parsedate_to_datetime(pub)
        return dt.isoformat(timespec='seconds') + 'Z'
    except Exception:
        return pub

# ─── Main conversion ────────────────────────────────────────────────────────────
OUT_FILE = 'dataset.jsonl'
PRE_DIR  = Path('preprocessed')  # use the preprocessed folder

with open(OUT_FILE, 'w', encoding='utf-8') as out:
    for root, _, files in os.walk(PRE_DIR):
        folder = Path(root).name
        for fn in files:
            if not fn.lower().endswith('.txt'):
                continue

            path = Path(root) / fn
            text = path.read_text(encoding='utf-8')
            # split off metadata / body
            if '\n\n' in text:
                meta_text, body = text.split('\n\n', 1)
            else:
                meta_text, body = text, ''

            data = parse_metadata(meta_text)
            rec = {
                'id':     Path(fn).stem,
                'type':   data.get('type', folder),
                'source': data.get('source', folder),
                'body':   body.strip()
            }

            # handle published URL/date/title fields
            if rec['type'] == 'news_articles':
                rec['title'] = data.get('title')
                if data.get('published'):
                    rec['published'] = normalize_published(data['published'])
                if data.get('url'):
                    rec['url'] = data['url']

            # statute
            elif rec['type'] == 'statute':
                rec['section']    = data.get('section')
                rec['title']      = data.get('title')
                rec['fine']       = data.get('fine')
                rec['jail_term']  = data.get('jail_term')

            # handbook
            elif rec['type'] == 'handbook':
                rec['module']       = data.get('module')
                rec['module_title'] = data.get('module_title')

            # regulation
            elif rec['type'] == 'regulation':
                rec['regulation'] = data.get('regulation')
                rec['item']       = data.get('item')
                # copy any extra keys you need
                for k in ('category_code','regulation_prefix','regulation_section',
                          'implements_section','fine_1_15_days','fine_16_30_days',
                          'fine_31_60_days','imprisonment_category','jail_possible','offense'):
                    if k in data:
                        rec[k] = data[k]

            # write one JSON per line
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')

print(f"✅ Wrote {OUT_FILE} from preprocessed/")  
