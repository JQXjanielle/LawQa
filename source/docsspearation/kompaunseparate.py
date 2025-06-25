import pdfplumber
import re
import os

def extract_compound_schedule(pdf_path):
    entries = []
    with pdfplumber.open(pdf_path) as pdf:
        # extract text from all pages
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    # split lines and find table rows starting with item number
    lines = text.splitlines()
    row_pattern = re.compile(r'^\s*(\d+)\s+([A-Z0-9]+)\s+(.+?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+)\s+(YA|TIDAK)', re.IGNORECASE)
    for line in lines:
        m = row_pattern.match(line)
        if m:
            item, category, sec_desc, f1, f2, f3, cat_juj, jail = m.groups()
            entries.append({
                "item": item,
                "category_code": category,
                "section_and_act": sec_desc.strip(),
                "fine_1_15": f1,
                "fine_16_30": f2,
                "fine_31_60": f3,
                "imprisonment_category": cat_juj,
                "jail_possible": jail.upper()
            })
    return entries

# Generate txt files for each entry
pdf_path = "source/pdfregulasi/Jadual-Kadar-Kompaun.pdf"
out_dir = "chunks/kompaun_schedule"
os.makedirs(out_dir, exist_ok=True)

entries = extract_compound_schedule(pdf_path)
for e in entries:
    fname = f"{out_dir}/compound_{e['item']}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"# source: Jadual-Kadar-Kompaun.pdf\n")
        f.write(f"# type: regulation\n")
        f.write(f"# regulation: Jadual Kadar Kompaun\n")
        f.write(f"# item: {e['item']}\n")
        f.write(f"# category_code: {e['category_code']}\n")
        f.write(f"# section_and_act: {e['section_and_act']}\n")
        f.write(f"# fine_1_15_days: {e['fine_1_15']}\n")
        f.write(f"# fine_16_30_days: {e['fine_16_30']}\n")
        f.write(f"# fine_31_60_days: {e['fine_31_60']}\n")
        f.write(f"# imprisonment_category: {e['imprisonment_category']}\n")
        f.write(f"# jail_possible: {e['jail_possible']}\n\n")
        # Offence description could be included as body, but we already have section_and_act
        f.write(f"{e['section_and_act']}\n")

print(f"Generated {len(entries)} compound schedule chunks.")


