#!/usr/bin/env python3
"""
Validate gender transformation output quality.

Checks transformed text for missed pronoun/title/term transformations
and prints a report with flagged passages.

Usage:
    python scripts/validate_transform.py books/output/pride-and-prejudice/all_female.json
    python scripts/validate_transform.py books/output/pride-and-prejudice/all_male.txt all_male
"""

import json
import re
import sys
from pathlib import Path

# ===========================================================================
# What to flag for each transform type
# ===========================================================================

# Word-boundary patterns that should NOT appear in a correctly transformed file.
# Values are the token that was supposed to replace them.
SHOULD_NOT_APPEAR = {
    "all_female": {
        # Binary male pronouns that should have become she/her/hers
        r"\bhe\b": "she",
        r"\bhim\b": "her",
        r"\bhis\b": "her/hers",
        r"\bhimself\b": "herself",
        r"\bMr\.": "Ms.",
        r"\bSir\b": "Madam",
        r"\bLord\b": "Lady",
        r"\bgentleman\b": "lady",
        r"\bgentlemen\b": "ladies",
    },
    "all_male": {
        r"\bshe\b": "he",
        r"\bher\b": "him/his",
        r"\bhers\b": "his",
        r"\bherself\b": "himself",
        r"\bMrs\.": "Mr.",
        r"\bMs\.": "Mr.",
        r"\bMiss\b": "Mr.",
        r"\bMadam\b": "Sir",
        r"\bLady\b": "Lord",
    },
    "nonbinary": {
        r"\bhe\b": "they",
        r"\bshe\b": "they",
        r"\bhim\b": "them",
        r"\bher\b": "them",
        r"\bhis\b": "their",
        r"\bhers\b": "their",
        r"\bhimself\b": "themselves",
        r"\bherself\b": "themselves",
        r"\bMr\.": "Mx.",
        r"\bMrs\.": "Mx.",
        r"\bMs\.": "Mx.",
        r"\bMiss\b": "Mx.",
    },
    "gender_swap": {
        # For gender_swap, flag pronouns that appear more than once in a row
        # (crude heuristic — perfect validation needs character map)
    },
}


def extract_paragraphs_from_json(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    paras = []
    for ch in data.get("chapters", []):
        for p in ch.get("paragraphs", []):
            if "sentences" in p:
                text = " ".join(p["sentences"])
            else:
                text = p.get("transformed_text") or p.get("text", "")
            if text.strip():
                paras.append(text)
    return paras


def extract_paragraphs_from_txt(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def validate(file_path: str, transform_type: str | None = None) -> None:
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Infer transform type from filename if not given
    if not transform_type:
        stem = path.stem.lower()
        for t in ("all_female", "all_male", "nonbinary", "gender_swap"):
            if t in stem:
                transform_type = t
                break
    if not transform_type:
        print("Could not infer transform type. Pass it as second argument.")
        sys.exit(1)

    rules = SHOULD_NOT_APPEAR.get(transform_type, {})
    if not rules:
        print(f"No validation rules defined for '{transform_type}' — skipping pattern checks.")

    # Load paragraphs
    if path.suffix == ".json":
        paragraphs = extract_paragraphs_from_json(path)
    else:
        paragraphs = extract_paragraphs_from_txt(path)

    print(f"\nValidating: {path.name} ({transform_type})")
    print(f"  {len(paragraphs)} paragraphs loaded")
    print()

    total_hits = 0
    flagged_paras: list[tuple[int, str, list[str]]] = []

    for idx, para in enumerate(paragraphs):
        hits = []
        for pattern, expected in rules.items():
            matches = re.findall(pattern, para, re.IGNORECASE)
            if matches:
                hits.append(f"'{matches[0]}' (should be '{expected}')")
        if hits:
            flagged_paras.append((idx + 1, para, hits))
            total_hits += len(hits)

    if not flagged_paras:
        print("  ✓ No missed transformations detected.\n")
    else:
        print(f"  ⚠ {total_hits} potential missed transformations in {len(flagged_paras)} paragraphs:\n")
        for para_num, para, hits in flagged_paras[:20]:  # cap output at 20
            print(f"  [Para {para_num}] {', '.join(hits)}")
            # Show 100-char snippet
            snippet = para[:120].replace("\n", " ")
            print(f"    …{snippet}…")
            print()
        if len(flagged_paras) > 20:
            print(f"  … and {len(flagged_paras) - 20} more paragraphs not shown.")

    # Summary score
    hit_rate = 1 - (total_hits / max(len(paragraphs), 1))
    pct = hit_rate * 100
    print(f"  Accuracy estimate: {pct:.1f}% clean paragraphs")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_transform.py <output_file> [transform_type]")
        sys.exit(1)
    validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
