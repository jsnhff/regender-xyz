"""Build a golden-chapter test file from the verified Gutenberg source.

Five chapters, ~6,700 words, about 5% of the book. Chosen by measured
coverage rather than instinct: between them they exercise every defect class
that reached the printed editions -- the King surname, Sir before a name,
bare vocatives, "pages", master/mistress, a letter salutation, three families
whose members share a surname, and both mid-book marriages.

Regenerate with:  python3 scripts/make_golden_chapters.py
"""

import json
import re
from pathlib import Path

B = "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice-finals/press_ready_files_82926/"
with open(B + "source_pg1342_61ch.json") as handle:
    book = json.load(handle)
by_number = {c["number"]: c for c in book["chapters"]}

GOLDEN = [
    (14, "pages (became 'handmaids'), Lady + name x6"),
    (27, "Mary King x2, Sir William x3, bare sir x3, master, shared surname"),
    (28, "Collins marries mid-chapter — the state change at ch28 p2"),
    (13, "Collins's letter: 'Dear Sir' salutation, bare vocatives x7"),
    (61, "Darcy & Bingley marry; Bennet/Bingley/Darcy all share surnames"),
]

ROMAN = {
    13: "XIII",
    14: "XIV",
    27: "XXVII",
    28: "XXVIII",
    61: "LXI",
}

out = [
    "Title: Pride & Prejudice (golden chapters)",
    "Author: Jane Austen",
    "",
]

for number, _why in GOLDEN:
    chapter = by_number[number]
    out.append(f"Chapter {ROMAN[number]}.]")
    out.append("")
    out.append("")
    for para in chapter["paragraphs"]:
        text = " ".join(para.get("sentences", [])).strip()
        if not text:
            continue
        # rewrap to the source's ~72 columns so it reads like the original
        words, line, lines = text.split(), "", []
        for word in words:
            if len(line) + len(word) + 1 > 72:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            lines.append(line)
        out.extend(lines)
        out.append("")
    out.append("")

path = Path("/Users/jasonhuff/regender-xyz test books/pride-prejudice-golden.txt")
path.write_text("\n".join(out), encoding="utf-8")

text = path.read_text(encoding="utf-8")
print(f"written: {path}")
print(f"  chapters: {len(GOLDEN)}   words: {len(text.split())}   chars: {len(text)}")
print("\n=== WHAT EACH ONE IS FOR ===")
for number, why in GOLDEN:
    words = len(
        " ".join(" ".join(p.get("sentences", [])) for p in by_number[number]["paragraphs"]).split()
    )
    print(f"  ch{number:<3} {words:5d} words  {why}")

print("\n=== COVERAGE CHECK ON THE FILE ===")
for name, pattern in [
    ("Mary/Miss King", r"(?:Mary|Miss|Mr\.)\s+King\b"),
    ("Sir + name", r"(?<![A-Za-z])Sir\s+[A-Z]"),
    ("Lady + name", r"(?<![A-Za-z])Lady\s+[A-Z]"),
    ("bare sir/madam/ma'am", r"(?<![A-Za-z])(?:sir|madam|ma’am)(?![A-Za-z])"),
    ("page(s)", r"(?<![A-Za-z])pages?(?![A-Za-z])"),
    ("master/mistress", r"(?<![A-Za-z])(?:master|mistress)(?![A-Za-z])"),
    ("Dear Sir salutation", r"Dear Sir"),
    ("Mrs. Collins (the ch28 change)", r"Mrs\. Collins"),
    ("Mrs. Darcy (the ch61 change)", r"Mrs\. Darcy"),
]:
    print(f"  {name:<32} {len(re.findall(pattern, text, re.I))}")
