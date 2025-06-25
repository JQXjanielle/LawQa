import os
import re
import shutil

src_dir = "source/txt"
dst_dir = "chunks/akta574"
os.makedirs(dst_dir, exist_ok=True)

for fn in os.listdir(src_dir):
    if not fn.endswith(".txt"):
        continue

    src_path = os.path.join(src_dir, fn)
    dst_path = os.path.join(dst_dir, fn)

    with open(src_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if metadata is present (look for "# source:")
    if not any(line.startswith("# source:") for line in lines[:3]):
        # Try to infer section number and title from filename or first line
        # e.g. filename "cederaparah.txt" -> section "338"? 
        # (You may need a mapping dict if filenames aren't numeric.)
        # For demo, extract number from the first digits in the filename:
        sec_match = re.search(r'(\d+)', fn)
        section = sec_match.group(1) if sec_match else "unk"
        # Extract title from the first non-blank line of the file:
        body_title = next((l.strip() for l in lines if l.strip()), "")
        title_match = re.match(r'^\d+\.\s*(.+)$', body_title)
        title = title_match.group(1) if title_match else body_title

        # Build the metadata header
        meta = [
            f"# source: Kanun Keseksaan (Akta 574)\n",
            f"# section: {section}\n",
            f"# title: {title}\n",
            "\n"
        ]
        lines = meta + lines

    # Write to destination
    with open(dst_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

print("All txt files moved to chunks/akta574 with metadata ensured.")
