"""Extract a paragraph-by-paragraph map of an IDML book for formatting review.

Reads an .idml, walks every story in page order, and emits one row per paragraph
with the applied paragraph style, the page the story starts on, a text preview,
and a flag when a paragraph looks like letter furniture but carries the plain
body style.

The point is to make style problems visible in a spreadsheet instead of by
scrolling InDesign: a signature that never got its Signature style shows up as a
MISSING_Signature row, and leftover Gutenberg `/* ... */` markers show up as
LEFTOVER_MARKER rows.

Letter conventions this checks against (read off the tuned template):
    Salutation   no first-line indent, space before  -- letter openings/closings
    Date Line    italic, no indent                   -- place/date headers
    Signature    right-aligned, space after          -- the name that signs off
    Letter Body  18pt left indent                    -- the quoted letter block

Detection is deliberately high-precision: it only calls a paragraph letter
furniture when the text is short and unmistakable, so a flagged row is worth
opening InDesign for. Body-block styling is a design call, so it is reported as
context inside each letter, never as an error.

Usage:
    python scripts/paragraph_map.py book.idml --csv map.csv --report map.md
    python scripts/paragraph_map.py book.idml --suspects-only
"""

import argparse
import csv
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

IDPKG = "{http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging}"

OPEN_Q = "[\"“‘']?"
CLOSE_Q = "[\"”’']?"

# A salutation is a short standalone line that opens a letter and ends in a comma.
SALUTATION_RE = re.compile(
    rf"^{OPEN_Q}(My dear(est)?|Dear|Madam|Sir)\b[^.!?]{{0,60}},{CLOSE_Q}$", re.IGNORECASE
)
# Closings: "Yours, etc." / "Your affectionate friend," / "I am, dear sir," etc.
CLOSING_RE = re.compile(
    rf"^{OPEN_Q}(Yours\b|Your (affectionate|sincere|obedient|dutiful)|I am, dear|"
    r"Adieu\b|Believe me\b)",
    re.IGNORECASE,
)
# Signatures are set as all-caps names: WILLIAM COLLINS. / EDW. GARDINER.
SIGNATURE_RE = re.compile(rf"^{OPEN_Q}[A-Z][A-Z.]*(\s+[A-Z][A-Z.]*)+[.,]?{CLOSE_Q}$")
# Date / place headers. Tight on purpose: a month name pinned to a day or year
# (so plain prose starting "May I ask..." never qualifies), or a street address.
MONTHS = (
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)
DATE_LINE_RE = re.compile(
    rf"\d{{1,2}}(st|nd|rd|th)?\s+{MONTHS}\b|{MONTHS}\s+\d{{1,2}}\b|"
    r"^[\"“]?[A-Z][\w']*\s+Street,",
)
MARKER_RE = re.compile(r"/\*|\*/")

BODY_STYLE = "Basic Paragraph BBB"
FURNITURE_STYLES = {"Chapter Numbers", "Chapter Header"}
# Styles that legitimately carry a letter line. A closing may be set as either
# Salutation (no indent) or Signature (right aligned) -- both read correctly.
OK_STYLES = {
    "salutation": {"Salutation"},
    "date_line": {"Date Line", "Salutation"},
    "signature": {"Signature"},
    "closing": {"Salutation", "Signature"},
}
LETTER_STYLES = {"Salutation", "Date Line", "Signature", "Letter Body"}
# Longest run of paragraphs we will treat as one letter before giving up.
MAX_LETTER_RUN = 30


def short_style(applied):
    """`ParagraphStyle/Basic Paragraph BBB` -> `Basic Paragraph BBB`."""
    if not applied:
        return "(none)"
    return applied.split("/", 1)[1] if "/" in applied else applied


def read_idml(path):
    """Return {archive_name: bytes} for every part in the package."""
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in zf.namelist()}


def spread_order(parts):
    """Spread archive names in designmap order."""
    root = ET.fromstring(parts["designmap.xml"])
    return [el.get("src") for el in root.iter(f"{IDPKG}Spread") if el.get("src")]


def page_index(parts, spreads):
    """Map story id -> [page labels], via each page's OverrideList."""
    story_pages = {}
    for spread_name in spreads:
        if spread_name not in parts:
            continue
        root = ET.fromstring(parts[spread_name])
        frame_to_page = {}
        for page in root.iter("Page"):
            label = page.get("Name") or "?"
            for frame_id in (page.get("OverrideList") or "").split():
                frame_to_page[frame_id] = label
        for frame in root.iter("TextFrame"):
            story = frame.get("ParentStory")
            if story:
                story_pages.setdefault(story, []).append(frame_to_page.get(frame.get("Self"), "?"))
    return story_pages


def story_order(parts, spreads):
    """Story ids in the order their first frame appears in the book."""
    ordered, seen = [], set()
    for spread_name in spreads:
        if spread_name not in parts:
            continue
        root = ET.fromstring(parts[spread_name])
        for frame in root.iter("TextFrame"):
            sid = frame.get("ParentStory")
            if sid and sid not in seen:
                seen.add(sid)
                ordered.append(sid)
    return ordered


def story_paragraphs(xml_bytes):
    """Yield (paragraph_style, char_styles, text) per paragraph in a story.

    Paragraphs are separated by <Br/> *inside* a ParagraphStyleRange, so a single
    range routinely holds dozens of paragraphs. Splitting on ranges instead of
    breaks is the classic way to miscount an IDML.
    """
    root = ET.fromstring(xml_bytes)
    story = root.find("Story")
    if story is None:
        return
    for psr in story.findall("ParagraphStyleRange"):
        style = psr.get("AppliedParagraphStyle")
        buf, char_styles = [], set()
        for csr in psr.findall("CharacterStyleRange"):
            cstyle = short_style(csr.get("AppliedCharacterStyle"))
            for node in csr:
                if node.tag == "Content":
                    if node.text:
                        buf.append(node.text)
                        if "No character style" not in cstyle:
                            char_styles.add(cstyle)
                elif node.tag == "Br":
                    yield style, sorted(char_styles), "".join(buf)
                    buf, char_styles = [], set()
        if "".join(buf).strip():
            yield style, sorted(char_styles), "".join(buf)


def classify(text):
    """Guess a letter role from the text alone. Returns "" when unsure."""
    s = text.strip()
    if not s:
        return ""
    if MARKER_RE.search(s):
        return "MARKER"
    if len(s) <= 60 and SIGNATURE_RE.match(s):
        return "signature"
    if len(s) <= 80 and CLOSING_RE.match(s):
        return "closing"
    # A header line is short, not a spoken sentence, and carries a real date.
    if len(s) <= 90 and s.count(" ") <= 12 and not re.search(r"[?!]", s) and DATE_LINE_RE.search(s):
        return "date_line"
    if len(s) <= 80 and SALUTATION_RE.match(s):
        return "salutation"
    return ""


def annotate(rows):
    """Attach roles, issues and letter ids. Mutates and returns `rows`."""
    letter_id = 0
    open_letter = None
    run = 0
    for row in rows:
        style = row["style"]
        role = "" if style in FURNITURE_STYLES else classify(row["text_full"])
        row["guess"] = role

        # Track letter extent so body paragraphs can be shown in context.
        opens = role in ("salutation", "date_line") or (style in LETTER_STYLES and role != "MARKER")
        if opens and open_letter is None:
            letter_id += 1
            open_letter = letter_id
            run = 0

        if open_letter is not None:
            run += 1
            row["letter"] = open_letter
            # A signature closes the letter. A bare closing may still be followed
            # by the signed name, so it does not close the block on its own.
            if role == "signature" or run >= MAX_LETTER_RUN:
                open_letter = None
        else:
            row["letter"] = ""

        issue = ""
        if role == "MARKER":
            issue = "LEFTOVER_MARKER"
        elif role and style not in OK_STYLES.get(role, set()):
            if style == BODY_STYLE or style == "(none)":
                issue = f"MISSING_{role}"
            else:
                issue = f"CHECK_{role}_is_{style.replace(' ', '_')}"
        row["issue"] = issue
    return rows


def build_map(path):
    """Return a list of row dicts, one per paragraph, in page order."""
    parts = read_idml(path)
    spreads = spread_order(parts)
    story_pages = page_index(parts, spreads)

    rows = []
    seq = 0
    chapter = 0
    for sid in story_order(parts, spreads):
        name = f"Stories/Story_{sid}.xml"
        if name not in parts:
            continue
        pages = story_pages.get(sid, [])
        start_page = pages[0] if pages else "?"
        paras = list(story_paragraphs(parts[name]))
        for style, _, text in paras:
            if short_style(style) in FURNITURE_STYLES and text.strip().isdigit():
                chapter = int(text.strip())
        for idx, (style, char_styles, text) in enumerate(paras, start=1):
            seq += 1
            rows.append(
                {
                    "seq": seq,
                    "chapter": chapter,
                    "page": start_page,
                    "story": sid,
                    "para": idx,
                    "style": short_style(style),
                    "guess": "",
                    "issue": "",
                    "letter": "",
                    "chars": len(text.strip()),
                    "char_styles": ",".join(char_styles),
                    "text": text.strip()[:200],
                    "text_full": text.strip(),
                }
            )
    return annotate(rows)


FIELDS = [
    "seq",
    "chapter",
    "page",
    "story",
    "para",
    "style",
    "guess",
    "issue",
    "letter",
    "chars",
    "char_styles",
    "text",
]


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows, path, source):
    issues = [r for r in rows if r["issue"]]
    style_counts = {}
    for r in rows:
        style_counts[r["style"]] = style_counts.get(r["style"], 0) + 1
    letters = {}
    for r in rows:
        if r["letter"]:
            letters.setdefault(r["letter"], []).append(r)

    out = [f"# Paragraph map — {source.split('/')[-1]}", ""]
    out.append(f"- Paragraphs: {len(rows)}")
    out.append(f"- Chapters: {max((r['chapter'] for r in rows), default=0)}")
    out.append(f"- Letters detected: {len(letters)}")
    out.append(f"- Paragraphs needing attention: {len(issues)}")
    out.append("")
    out.append("## Paragraph styles in use")
    out.append("")
    out.append("| Style | Paragraphs |")
    out.append("| --- | ---: |")
    for style, count in sorted(style_counts.items(), key=lambda kv: -kv[1]):
        out.append(f"| {style} | {count} |")
    out.append("")
    out.append("## Paragraphs needing attention")
    out.append("")
    if not issues:
        out.append("None.")
    else:
        out.append("| Ch | Page | Issue | Applied style | Text |")
        out.append("| ---: | ---: | --- | --- | --- |")
        for r in issues:
            text = r["text"].replace("|", "\\|")[:80]
            out.append(f"| {r['chapter']} | {r['page']} | {r['issue']} | {r['style']} | {text} |")
    out.append("")
    out.append("## Letter styling coverage")
    out.append("")
    out.append("One row per letter. `-` means no paragraph in that letter carries")
    out.append("the style, which is worth a look when its neighbours do.")
    out.append("")
    out.append("| Letter | Ch | Page | Salutation | Date Line | Letter Body | Signature | Issues |")
    out.append("| ---: | ---: | ---: | --- | --- | --- | --- | ---: |")
    for lid in sorted(letters):
        block = letters[lid]
        styles = [r["style"] for r in block]
        bad = sum(1 for r in block if r["issue"])

        def mark(name, styles=styles):
            n = styles.count(name)
            return str(n) if n else "-"

        out.append(
            f"| {lid} | {block[0]['chapter']} | {block[0]['page']} | "
            f"{mark('Salutation')} | {mark('Date Line')} | {mark('Letter Body')} | "
            f"{mark('Signature')} | {bad or '-'} |"
        )
    out.append("")
    out.append("## Every detected letter, paragraph by paragraph")
    out.append("")
    out.append("Check each block reads: opening, optional date line, body, signature.")
    out.append("")
    for lid in sorted(letters):
        block = letters[lid]
        ch = block[0]["chapter"]
        page = block[0]["page"]
        out.append(f"### Letter {lid} — chapter {ch}, from page {page}")
        out.append("")
        out.append("| Style | Guess | Issue | Text |")
        out.append("| --- | --- | --- | --- |")
        for r in block:
            text = r["text"].replace("|", "\\|")[:80]
            out.append(f"| {r['style']} | {r['guess'] or '-'} | {r['issue'] or '-'} | {text} |")
        out.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Map IDML paragraphs and their styles.")
    ap.add_argument("idml", help="path to the .idml to map")
    ap.add_argument("--csv", help="write the full paragraph map here")
    ap.add_argument("--report", help="write a markdown summary here")
    ap.add_argument(
        "--suspects-only", action="store_true", help="print only paragraphs with an issue"
    )
    args = ap.parse_args()

    rows = build_map(args.idml)
    if args.csv:
        write_csv(rows, args.csv)
    if args.report:
        write_report(rows, args.report, args.idml)

    if not args.csv and not args.report:
        shown = [r for r in rows if r["issue"]] if args.suspects_only else rows
        for r in shown:
            print(
                f"ch{r['chapter']:>3} p{r['page']:>4} {r['style']:<20} "
                f"{r['issue'] or '-':<22} {r['text'][:66]}"
            )
    issues = sum(1 for r in rows if r["issue"])
    print(f"{len(rows)} paragraphs, {issues} needing attention", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
