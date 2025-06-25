import pdfplumber
import re
import os

def extract_clean_text_regulasi(pdf_path, toc_pages=0, footer_pat=None):
    """
    Extracts and cleans text from the Demerit-Points PDF:
      - (Optionally) skip a TOC prefix if present
      - Strip running headers/footers
      - Remove stray ALL-CAPS lines
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.splitlines()
            # Drop any leading ALL-CAPS header line
            if lines and re.match(r'^[A-Z0-9\s\-\(\)]+$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))

    full = "\n\n".join(pages)

    # remove any stray ALL-CAPS header/footer lines
    full = re.sub(r'(?m)^[A-Z0-9\s\-\(\)]+$', '', full)

    # remove any blank‐line clusters
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full

def chunk_regulasi_demerit(text):
    """
    Splits on each table row number, e.g. "1. Subseksyen 43(1) ..." 
    Returns list of (row_num, chunk_text).
    """
    # split at each line that begins with a digit + dot + space
    parts = re.split(r'(?m)(?=^\s*\d+\.\s)', text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # extract the row number
        m = re.match(r'^(\d+)\.\s', part)
        row_id = m.group(1) if m else "unk"
        chunks.append((row_id, part))
    return chunks

if __name__ == "__main__":
    pdf = "source/pdfregulasi/9.1-INFORMASI_K-KESALAHAN-BERJADUAL-DAN-MATA-DEMERIT-PINDAAN-TERKINI-2022-new.pdf"
    clean = extract_clean_text_regulasi(pdf)
    rows = chunk_regulasi_demerit(clean)

    out_dir = "chunks/handbook_regulasi_demerit"
    os.makedirs(out_dir, exist_ok=True)

    for row_id, content in rows:
        fname = f"{out_dir}/Demerit_{row_id}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            # metadata header
            f.write(f"# source: 9.1-INFORMASI_K-KESALAHAN-BERJADUAL-DAN-MATA-DEMERIT-2022.pdf\n")
            f.write(f"# type: handbook\n")
            f.write(f"# regulation: Kaedah Kesalahan Berjadual & Mata Demerit\n")
            f.write(f"# item: {row_id}\n\n")
            # the full table-row text
            f.write(content)

    print(f"Generated {len(rows)} demerit‐point chunks in {out_dir}")

















