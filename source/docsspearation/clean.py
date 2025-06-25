import pdfplumber
import re
import os

def extract_clean_text(pdf_path, toc_pages=17, footer_pages=7):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            if idx < toc_pages or idx >= total - footer_pages:
                continue
            text = page.extract_text() or ""
            lines = text.splitlines()
            if lines and re.match(r'^[^\.\?!]+\s\d+$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))

    full = "\n\n".join(pages)

    def remove_stray_headers(full_text):
        lines = full_text.splitlines()
        cleaned, i = [], 0
        header_pat = re.compile(r'^[^\.\?!]+\s\d+$')
        while i < len(lines):
            line = lines[i].strip()
            if header_pat.match(line):
                if i + 1 < len(lines) and lines[i+1].strip() == "KTA":
                    i += 2
                else:
                    i += 1
            else:
                cleaned.append(lines[i])
                i += 1
        return "\n".join(cleaned)

    full = remove_stray_headers(full)
    full = re.sub(r'(?m)^[ \t]*KTA[ \t]*\n?', '', full)
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full

def chunk_by_numbered_sections(text):
    """
    Splits before any line that starts with:
       digits + optional uppercase letter + dot + space
    e.g. "1. ", "25. ", "25A. "
    """
    parts = re.split(r'(?m)(?=^[0-9]+[A-Z]?\.\s)', text)
    chunks = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        chunks.append(p)
    return chunks

if __name__ == "__main__":
    pdf_path = "source/pdfakta/Akta 715 (AKTA PENGANGKUTAN AWAM ).pdf"
    clean_text = extract_clean_text(pdf_path, toc_pages=17, footer_pages=7)
    sections = chunk_by_numbered_sections(clean_text)

    os.makedirs("chunks/akta715", exist_ok=True)
    for idx, sec in enumerate(sections, 1):
        m = re.match(r'^([0-9]+[A-Z]?)\.', sec)
        sec_id = m.group(1) if m else f"unk{idx}"
        fname = f"chunks/akta715/715_Seksyen{sec_id}_{idx}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# source: Akta 715\n")
            f.write(f"# section: {sec_id}\n")
            f.write(sec)

    print(f"Generated {len(sections)} section chunks.")





