import os
import re
import pdfplumber

PDF_PATH   = "source/pdfakta/Akta-334.pdf"
OUT_DIR    = "chunks/akta334"

def extract_clean_text_334(pdf_path, toc_pages=8, footer_start=77, footer_end=81):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            # skip TOC pages 0–7, and footer pages 76–80 (0-based)
            if idx < toc_pages or footer_start-1 <= idx <= footer_end-1:
                continue
            text = page.extract_text() or ""
            lines = text.splitlines()
            # drop running header if ALL CAPS + digits
            if lines and re.match(r'^[A-Z\s]+(?:\d+)?$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))

    full = "\n\n".join(pages)
    # drop any stray all-caps header lines
    full = re.sub(r'(?m)^[A-Z\s]+(?:\d+)?\s*$', '', full)
    # drop any stray "KTA" lines
    full = re.sub(r'(?m)^[ \t]*KTA[ \t]*$', '', full)
    # collapse 3+ blanks
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full.strip()

def chunk_sections_334(text):
    """
    Split before any line that begins with:
      optional spaces + digits + optional letter + optional spaces + dot + space
    e.g. "1.", "1A.", "1 A.", "   10B . "
    """
    # split lookahead
    parts = re.split(r'(?m)(?=^\s*\d+(?:\s*[A-Za-z])?\s*\.\s)', text)
    header_re = re.compile(r'^\s*(\d+)(?:\s*([A-Za-z]))?\s*\.\s')
    chunks = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        m = header_re.match(p)
        if m:
            num, letter = m.group(1), (m.group(2) or '').upper()
            sec_id = f"{num}{letter}"
        else:
            sec_id = "unk"
        chunks.append((sec_id, p))
    return chunks

if __name__ == "__main__":
    clean = extract_clean_text_334(PDF_PATH)
    sections = chunk_sections_334(clean)

    os.makedirs(OUT_DIR, exist_ok=True)
    for idx, (sec_id, sec_text) in enumerate(sections, 1):
        fname = f"334_Seksyen{sec_id}_{idx}.txt"
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"# source: Akta 334\n")
            f.write(f"# section: {sec_id}\n\n")
            f.write(sec_text)

    print(f"✔ Generated {len(sections)} chunks in {OUT_DIR}")

