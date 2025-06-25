import pdfplumber, re, os

def extract_clean_text_748(pdf_path, toc_pages=6, first_footer_page=34):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        # calculate footer cutoff index (0-based)
        footer_start = first_footer_page - 1
        for idx, page in enumerate(pdf.pages):
            # skip TOC and everything from page 34 onward
            if idx < toc_pages or idx >= footer_start:
                continue
            text = page.extract_text() or ""
            lines = text.splitlines()
            # drop first line if it ends with a page number
            if lines and re.match(r'^.*\d+$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))

    # join all kept pages
    full = "\n\n".join(pages)

    # remove any stray header lines (e.g. "Undang-Undang Malaysia 7", "Institut ... 9")
    full = re.sub(r'(?m)^[^\.\?!]+\s+\d+\s*$', '', full)

    # collapse excessive blank lines
    full = re.sub(r'\n{3,}', '\n\n', full)

    return full

def chunk_by_numbered_sections(text):
    # split at lines starting with "N. " (digit dot space)
    parts = re.split(r'(?m)^(?=\d+\.\s)', text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # grab the section number
        m = re.match(r'^(\d+)\.', part)
        sec_id = m.group(1) if m else "unk"
        chunks.append((sec_id, part))
    return chunks

if __name__ == "__main__":
    pdf_path = "source/pdfakta/Akta MIROS 2012 BM_fixed.pdf"
    clean = extract_clean_text_748(pdf_path)
    sections = chunk_by_numbered_sections(clean)

    out_dir = "chunks/akta748"
    os.makedirs(out_dir, exist_ok=True)
    for idx, (sec_id, sec_text) in enumerate(sections, 1):
        fname = f"{out_dir}/748_Seksyen{sec_id}_{idx}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# source: Akta 748\n")
            f.write(f"# section: {sec_id}\n")
            f.write(sec_text)

    print(f"Generated {len(sections)} chunks in {out_dir}")




