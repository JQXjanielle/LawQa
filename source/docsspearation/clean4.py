import os
import re
import pdfplumber

def extract_clean_text_333(pdf_path, toc_pages=12, footer_start=215):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        skip_from = footer_start - 1
        for idx, page in enumerate(pdf.pages):
            if idx < toc_pages or idx >= skip_from:
                continue
            text = page.extract_text() or ""
            lines = text.splitlines()
            if lines and re.match(r'^[A-Z\s]+(?:\d+)?$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))
    full = "\n\n".join(pages)
    full = re.sub(r'(?m)^[A-Z\s]+(?:\d+)?\s*$', '', full)
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full


def chunk_sections_333(text):
    """
    1) Drop anything before the first heading.
    2) Split before any line that starts with:
         digits + optional whitespace + optional uppercase letter
         + optional whitespace + dot + space
       e.g. "45.", "45 A.", "45A ."
    3) Normalize section ID to digits+letter (no spaces).
    """
    # 1) Remove preamble up to first numbered line
    parts = re.split(r'(?m)^(?=\d+\s*[A-Za-z]?\s*\.\s)', text)
    if parts and not re.match(r'^\d+\s*[A-Za-z]?\s*\.\s', parts[0]):
        parts = parts[1:]

    chunks = []
    header_re = re.compile(r'^(\d+)\s*([A-Za-z]?)\s*\.\s')
    for part in parts:
        p = part.strip()
        if not p:
            continue
        # 2) Extract and normalize the section ID
        m = header_re.match(p)
        if m:
            num, letter = m.group(1), m.group(2).upper()
            sec_id = f"{num}{letter}"
        else:
            sec_id = "unk"
        chunks.append((sec_id, p))
    return chunks

if __name__ == "__main__":
    pdf_path = "source/pdfakta/Akta-Pengangkutan-Jalan-1987-Akta-333.pdf"
    clean = extract_clean_text_333(pdf_path)
    sections = chunk_sections_333(clean)

    out_dir = "chunks/akta333"
    os.makedirs(out_dir, exist_ok=True)
    for idx, (sec_id, sec_text) in enumerate(sections, start=1):
        fname = f"{out_dir}/333_Seksyen{sec_id}_{idx}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# source: Akta 333\n")
            f.write(f"# section: {sec_id}\n\n")
            f.write(sec_text)

    print(f"Generated {len(sections)} section chunks in {out_dir}")










