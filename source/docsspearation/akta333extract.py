import os
import re
import string
import pdfplumber

PDF_PATH    = "source/pdfakta/Akta-Pengangkutan-Jalan-1987-Akta-333.pdf"
CHUNKS_DIR  = "chunks/akta333"
TOC_PAGES   = 12
FOOTER_FROM = 215  # 1-based

def extract_clean_text_333(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        skip_from = FOOTER_FROM - 1
        for i, page in enumerate(pdf.pages):
            if i < TOC_PAGES or i >= skip_from:
                continue
            txt = page.extract_text() or ""
            lines = txt.splitlines()
            if lines and re.match(r'^[A-Z\s]+(?:\d+)?$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))
    full = "\n\n".join(pages)
    full = re.sub(r'(?m)^[A-Z\s]+(?:\d+)?\s*$', '', full)
    full = re.sub(r'\n{3,}', '\n\n', full).strip()
    return full

def split_chunks(text):
    parts = re.split(r'(?m)(?=^\s*\d+(?:\s*[A-Za-z])?\s*\.\s)', text)
    header_re = re.compile(r'^\s*(\d+)(?:\s*([A-Za-z]))?\s*\.\s')
    chunks = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        m = header_re.match(p)
        if m:
            sec = f"{m.group(1)}{(m.group(2) or '').upper()}"
        else:
            sec = "unk"
        chunks.append((sec, p))
    return chunks

def extract_titles(full_text):
    header_re = re.compile(r'^\s*(\d+)(?:\s*([A-Za-z]))?\s*\.\s')
    titles = {}
    lines = full_text.splitlines()
    for idx, line in enumerate(lines):
        m = header_re.match(line)
        if not m:
            continue
        base = m.group(1)
        if idx == 0:
            title = ""
        else:
            prev = lines[idx-1].strip()
            if prev and prev[0].islower() and idx >= 2:
                prev2 = lines[idx-2].strip()
                title = f"{prev2} {prev}"
            else:
                title = prev
        titles.setdefault(base, title)
    return titles

def disambiguate_duplicates(chunks):
    grouped = {}
    for sec, body in chunks:
        # derive base by capturing leading digits, or fallback to sec itself
        m = re.match(r'^(\d+)', sec)
        base = m.group(1) if m else sec
        grouped.setdefault(base, []).append((sec, body))

    result = []
    for base, items in grouped.items():
        if len(items) == 1:
            result.append(items[0])
        else:
            for i, (orig_sec, body) in enumerate(items):
                if i == 0:
                    # first occurrence keeps base
                    result.append((base, body))
                else:
                    # suffix A, B, ...
                    suffix = string.ascii_uppercase[i-1]
                    result.append((f"{base}{suffix}", body))
    return result

if __name__ == "__main__":
    os.makedirs(CHUNKS_DIR, exist_ok=True)

    full = extract_clean_text_333(PDF_PATH)
    raw = split_chunks(full)
    numbered = disambiguate_duplicates(raw)
    titles = extract_titles(full)

    for idx, (sec, body) in enumerate(numbered, start=1):
        fname = f"333_Seksyen{sec}_{idx}.txt"
        path = os.path.join(CHUNKS_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# source: Akta 333\n")
            f.write(f"# section: {sec}\n")
            # lookup title by numeric base
            m = re.match(r'^(\d+)', sec)
            base = m.group(1) if m else sec
            title = titles.get(base, "")
            if title:
                f.write(f"# title: {title}\n")
            f.write("\n")
            f.write(body + "\n")

    print(f"✔ Generated {len(numbered)} chunks with titles in {CHUNKS_DIR}")




