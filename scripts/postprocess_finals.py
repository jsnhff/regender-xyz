"""
Post-process P&P finals .txt files to catch gendered language the LLM
misses when treating character name honorifics as proper nouns.

Fixes applied:
  - "they was" → "they were"  (singular-they verb agreement)
  - "Miss [A-Z]..." → "Mx. ..." (only title form; verb "miss" is lowercase)
  - "Mr. " / "Mrs. " → "Mx. "
  - "_Miss X_" → "_Mx. X_" (italic markup edge case)

Run after transforms complete:
  python scripts/postprocess_finals.py [--all-female] [--all-male] [--gender-swap] [--nonbinary]
Or process all:
  python scripts/postprocess_finals.py
"""

import re
import sys
from pathlib import Path

FINALS_DIR = Path("books/output/pride-and-prejudice-finals")


def postprocess(path: Path, transform_type: str) -> None:
    if not path.exists():
        print(f"  SKIP {path.name} (not found)")
        return

    text = path.read_text()
    original_len = len(text)

    # Only apply gendered-title fixes to nonbinary; other transforms handle
    # Mr/Mrs/Miss differently (all_male → he, all_female → she, etc.)
    if transform_type == "nonbinary":
        fixes = [
            (r"\bThey was\b", "They were"),
            (r"\bthey was\b", "they were"),
            (r"\bMiss (?=[A-Z])", "Mx. "),
            (r"\bMrs\. ", "Mx. "),
            (r"\bMr\. ", "Mx. "),
            (r"_Miss ([A-Z])", r"_Mx. \1"),
            (r"\bLadyship\b", "Nobleship"),
            (r"\blordship\b", "nobleship"),
            (r"\bNibbling\b", "Nibling"),
            (r"\bnibbling\b", "nibling"),
        ]
    else:
        # For gendered transforms, only fix verb agreement
        fixes = [
            (r"\bThey was\b", "They were"),
            (r"\bthey was\b", "they were"),
        ]

    total = 0
    for pattern, replacement in fixes:
        count = len(re.findall(pattern, text))
        text = re.sub(pattern, replacement, text)
        if count:
            print(f"    {pattern!r:45} → {replacement!r}: {count}")
        total += count

    path.write_text(text)
    print(f"  {path.name}: {total} fixes applied")


def main() -> None:
    targets = [
        ("nonbinary.txt", "nonbinary"),
        ("all_female.txt", "all_female"),
        ("all_male.txt", "all_male"),
        ("gender_swap.txt", "gender_swap"),
    ]

    args = sys.argv[1:]
    if args:
        requested = {a.lstrip("-").replace("-", "_") for a in args}
        targets = [(f, t) for f, t in targets if t in requested]

    for filename, ttype in targets:
        print(f"\nProcessing {filename}...")
        postprocess(FINALS_DIR / filename, ttype)


if __name__ == "__main__":
    main()
