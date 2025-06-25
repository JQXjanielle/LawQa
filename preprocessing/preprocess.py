import os
import re
import unicodedata
import malaya
from malaya.text.function import get_stopwords, remove_html_tags
from malaya.tokenizer import Tokenizer

# ------------ Malaya setup ------------
stopwords = set(get_stopwords())
tokenizer = Tokenizer().tokenize
try:
    stemmer = malaya.stem.sastrawi()
except Exception:
    stemmer = malaya.stem.naive()

# ------------ Helpers ------------
def normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text).lower()

def strip_numbering_and_list_markers(text: str) -> str:
    text = re.sub(r'(?m)^\s*\d+\.\s*\(\d+\)\s*', '', text)
    text = re.sub(r'(?m)^\s*\([a-z]\)\s*', '', text)
    return text

def preprocess_and_stem(text: str) -> str:
    text = strip_numbering_and_list_markers(text)
    text = normalize_text(text)
    toks = tokenizer(text)
    toks = [t for t in toks if t not in stopwords]
    joined = " ".join(toks)
    stemmed = stemmer.stem(joined)
    return stemmed

def preprocess_no_stem(text: str) -> str:
    # 1) strip HTML, normalize casing/accents
    text = remove_html_tags(text)
    text = normalize_text(text)

    # 2) remove URLs
    text = re.sub(r'https?://\S+', '', text)
    #    remove anything containing “.com”
    text = re.sub(r'\b\S*\.com\S*\b', '', text)

    # 3) remove trailing copyright segments
    text = re.sub(r'©.*$', '', text)

    # 4) remove dates
    text = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', text)
    text = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '', text)
    text = re.sub(
        r'\b\d{1,2}\s+(?:Jan|Feb|Mac|Apr|Mei|Jun|Jul|Ogos|Sep|Okt|Nov|Dis)[a-z]*\s+\d{2,4}\b',
        '',
        text, flags=re.IGNORECASE
    )

 
    toks = tokenizer(text)
    toks = [t for t in toks if t not in stopwords]

    return " ".join(toks)

def dispatch_preprocess(file_path: str, body: str) -> str:
    folder = file_path.replace('\\','/').split('/')[-2]
    if folder == 'news_articles':
        return preprocess_no_stem(body)
    else:
        return preprocess_and_stem(body)

# ------------ Main Loop ------------
SRC_ROOT = 'chunks'
DST_ROOT = 'preprocessed'

for subdir, _, files in os.walk(SRC_ROOT):
    rel_dir = os.path.relpath(subdir, SRC_ROOT)
    out_dir = os.path.join(DST_ROOT, rel_dir)
    os.makedirs(out_dir, exist_ok=True)

    for fn in files:
        if not fn.lower().endswith('.txt'):
            continue
        src_path = os.path.join(subdir, fn)
        content = open(src_path, encoding='utf-8').read()
        if '\n\n' in content:
            meta, body = content.split('\n\n', 1)
        else:
            meta, body = content, ''
        clean_body = dispatch_preprocess(src_path, body)
        dst_path = os.path.join(out_dir, fn)
        with open(dst_path, 'w', encoding='utf-8') as f:
            f.write(meta + '\n\n' + clean_body)

print("✅ Preprocessing complete, outputs in 'preprocessed/'") 






