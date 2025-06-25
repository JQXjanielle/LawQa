import pdfplumber
import re
import os

# Define your modules and their (1-based) page ranges
MODULE_RANGES = {
    "intro":   (7, 28),
    "KPP01":   (33, 173),
    "KPP02":   (182, 222),
    "KPP02L":  (227, 283),  # “KPP02 Litar”
    "KPP03":   (291, 365),
}

def extract_clean_text_range(pdf_path, start_page, end_page):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        # pdf.pages is 0-based, so subtract 1
        for idx in range(start_page - 1, end_page):
            page = pdf.pages[idx]
            text = page.extract_text() or ""
            lines = text.splitlines()
            # drop any running header (ALL-CAPS ± digits)
            if lines and re.match(r'^[A-Z\s]+(?:\d+)?$', lines[0].strip()):
                lines = lines[1:]
            pages.append("\n".join(lines))
    full = "\n\n".join(pages)
    # drop stray all-caps header lines
    full = re.sub(r'(?m)^[A-Z\s]+(?:\d+)?\s*$', '', full)
    # drop footer lines like "332 " or " 332"
    full = re.sub(
        r'(?m)^[ \t]*(?:\d+\s*[]|[]\s*\d+)[ \t]*\n?', '',
        full
    )
    # drop any leftover "Kurikulum Pendidikan Pemandu"
    full = re.sub(r'(?m)^\s*Kurikulum Pendidikan Pemandu\s*$', '', full)
    # collapse blank lines
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full

def chunk_handbook_module(text, module_id):
    """
    Split chapter text on N.M headings, tag with module_id.
    """
    parts = re.split(r'(?m)(?=^\d+\.\d+\s)', text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.match(r'^(\d+)\.(\d+)\s+(.+)', part)
        if not m: continue
        section_id = f"{m.group(1)}.{m.group(2)}"
        chunks.append((module_id, section_id, part))
    return chunks

if __name__ == "__main__":
    pdf_path = "source/pdfhb/KPP_D.pdf"
    out_base = "chunks/handbook_kppd"
    os.makedirs(out_base, exist_ok=True)

    total = 0
    for module_id, (start, end) in MODULE_RANGES.items():
        text = extract_clean_text_range(pdf_path, start, end)
        lessons = chunk_handbook_module(text, module_id)
        mod_dir = os.path.join(out_base, module_id)
        os.makedirs(mod_dir, exist_ok=True)

        for module_id, section_id, content in lessons:
            fname = f"{module_id}_{section_id}.txt"
            with open(os.path.join(mod_dir, fname), "w", encoding="utf-8") as f:
                f.write(f"# source: KPP_D.pdf\n")
                f.write(f"# type: handbook\n")
                f.write(f"# module: {module_id}\n")
                f.write(f"# section: {section_id}\n\n")
                f.write(content)
            total += 1

    print(f"Generated {total} chunks across {len(MODULE_RANGES)} modules.")





