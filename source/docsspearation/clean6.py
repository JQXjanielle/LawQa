import os
import re

# Directory containing the demerit handbook chunks
chunk_dir = "chunks/handbook_regulasi_demerit"

# Patterns
item_meta_pattern = re.compile(r'^# item:\s*(\d+)', re.IGNORECASE)
leading_dash_pattern = re.compile(r'^\s*-\s*(\d+)')          # "- 10" at start
trailing_nums_pattern = re.compile(r'\s*(\d+)(?:\s+\d+)*\s*$') # trailing "10", "10 10", etc.

for filename in os.listdir(chunk_dir):
    if not filename.endswith(".txt"):
        continue

    filepath = os.path.join(chunk_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Locate the first content line (after a blank line)
    content_idx = next(i for i, line in enumerate(lines) if line.strip() == "") + 1
    first_line = lines[content_idx]

    # 1) Determine demerit_points
    if leading_dash_pattern.match(first_line):
        demerit_points = "0"
    else:
        m = trailing_nums_pattern.search(first_line)
        demerit_points = m.group(1) if m else "0"

    # 2) Clean that first line: remove leading "- " and all trailing digits/spaces/hyphens
    cleaned = re.sub(r'^\s*-\s*', '', first_line)
    cleaned = re.sub(r'[\s\d\-]+$', '', cleaned).rstrip() + "\n"
    lines[content_idx] = cleaned

    # 3) Inject metadata
    new_content = []
    for line in lines:
        new_content.append(line)
        if item_meta_pattern.match(line):
            new_content.append(f"# demerit_points: {demerit_points}\n")

    # 4) Write back
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_content)

print("Demerit points metadata added and first lines cleaned.") 

