# Known Parser Bugs

_Logged 2026-04-18. These are pre-existing issues unrelated to Roman numeral or metadata fixes landed today._

---

## Great Expectations (pg1400)
- **Title wrong**: extracts `[1867 Edition]` instead of "Great Expectations" — the bracketed edition marker appears before the real title in that Gutenberg header
- **Chapter count off**: 62 detected vs 59 expected — 3 extra chapters from preface/intro sections being counted

## Frankenstein (pg84)
- **Title wrong**: extracts `or, the Modern Prometheus` (subtitle line) instead of "Frankenstein"
- **Chapter ordering**: "Chapter 24" sorts first in the chapter list — the final chapter of a preface/frame narrative gets indexed before the main novel chapters

## A Tale of Two Cities (pg98)
- **First chapter wrong**: "Chapter 6: The Shoemaker" appears before Chapter 1 — the TOC skip (`_find_content_start`) is failing to detect the end of the table of contents, treating the last TOC entry as real content

## Huckleberry Finn (pg76)
- **Title wrong**: extracts `(Tom Sawyer's Comrade)` (subtitle/series note) instead of "Adventures of Huckleberry Finn"
- **Chapter count off by 1**: 42 detected vs 43 expected

## Sherlock Holmes (pg1661)
- **Adventure I missing + scrambled order**: known bug, tracked in memory (bug_sherlock_adventure_i.md)
- Chapters duplicated and out of sequence; Adventure I never appears

## Anne of Green Gables (pg45)
- **Title all-caps**: "ANNE OF GREEN GABLES" — title extraction preserves source capitalization; should apply title-case normalization

---

## Update 2026-08-29 — illustration-split paragraphs

One cause common to several of the above was found and fixed on
`claude/repo-state-5ylut4`: illustrated Gutenberg editions place plates in the
middle of a sentence, and the parser removed the plate but left the blank lines
around it, splitting one paragraph in two.

In the P&P sample that was 1 split across 20 plates, and it reached print as a
paragraph indent arriving mid-sentence. It also costs transform accuracy at that
point, since the model gets a fragment ending on a bare possessive with the noun
it belongs to in a different paragraph.

Every title listed above is an illustrated edition, so **re-parse and re-check
each one** — some of the chapter-count discrepancies here may be this. QC now
reports the pattern as `split_sentence`.

The title-extraction bugs (bracketed edition markers, subtitles, all-caps) are
untouched and still open.
