---
name: idml
description: Rules for generating IDML book layouts from P&P finals JSON using Matt's fresh template (book_template.idml). Use 'Basic Paragraph BBB' style, chapter opener rectos are heading-only (body starts on next spread), override Master B frames at their exact master geometry, inject Italic character style, validate with in-script audit + subagent + advisor before declaring done. Invoke whenever generating or modifying IDML output for the P&P pipeline.
---

# IDML Generation (current pipeline)

The current pipeline is `scripts/layout_book.py` → produces `books/output/pride-and-prejudice-finals/{variant}.idml` from `{variant}.json` + `book_template.idml`. The old `scripts/make_idml.py` is reference only — do not invoke it; it targets a different template.

## Template facts (book_template.idml)

| Concern | Value |
|---|---|
| Body paragraph style | `ParagraphStyle/Basic Paragraph BBB` (9.75pt BBB Baskervvol Book, 13pt leading, 18pt first-line indent) |
| Chapter title style | `ParagraphStyle/Chapter Header` (11pt all-caps, 440 tracking, centered) |
| Chapter number style | `ParagraphStyle/Chapter Numbers` (PicNic font, large — Matt tunes per book to fit double-digit chapters without overflow) |
| Italic character style | **NOT in template** — script must inject `CharacterStyle/Italic` with `FontStyle="Italic"` into `Resources/Styles.xml` |
| Master A (`ud8`) | Body pages, both verso + recto. Primary text frames `u6392` (verso) / `u6396` (recto), 225×423pt |
| Master B (`ue8dd`) | Chapter opener recto. Frames: `ue961` body (suppress on opener — body starts next page), `ue977` chapter number, `ue990` "CHAPTER" label |
| Page size | 4.25" × 6.875" (306 × 495 pt). Spread Y-stride 693pt |

## Architectural rules (load-bearing — violating these silently breaks output)

1. **Chapter opener recto is heading-only.** Master B's body frame `ue961` is suppressed on opener pages. Body text starts on the **verso of the next spread**, not on the opener recto. This is Matt's parent design intent; do not put a shortened body frame on the opener.

2. **Use Master B's exact frame geometry for the number and label.** Override `ue977` with a concrete frame at spread x=45.53–270 / y=-184.54–151.17 (i.e. `ItemTransform="1 0 0 1 157.77 -16.69"`, half-extents 112.24×167.85). Override `ue990` at spread x=45–267.89 / y=-119.52–-97.92 (`ItemTransform="1 0 0 1 156.45 -108.72"`, half-extents 111.45×10.80). The master's `ue977` looks "parked off-canvas" because of compound translate+anchor offsets — compute net spread coords before re-emitting.

3. **Chapter label content is just `"CHAPTER"`** (no number suffix). The big PicNic numeral below provides the chapter number.

4. **Per-chapter Story isolation.** Each chapter has its own `Story_<id>.xml` for body text. Chains never cross chapter boundaries. The opener recto has no body frame, so the next chapter's heading can never bleed onto a previous chapter's body recto.

5. **Recto parity.** Every opener spread asserts `verso_page_num % 2 == 0` (so the Master B recto lands on odd = recto). If a chapter has K body frames, K can be even or odd — parity holds because each spread advances `page_num` by 2.

6. **Master frame placeholder stories must stay in the ZIP.** `Stories/Story_ue94b.xml`, `ue97a.xml`, `ue993.xml`, `ue9b5.xml`, `ue9ce.xml`, `ue9e7.xml`, `uea00.xml` are referenced by master XML — deleting them breaks the IDML even when every page overrides those frames. Same applies to Master A's `u637e`, `u5ff1`, `u600a`, `u6023`, `u603d`.

7. **Italic character style injection.** Insert before `</RootCharacterStyleGroup>` in `Resources/Styles.xml`:
   ```xml
   <CharacterStyle Self="CharacterStyle/Italic" Name="Italic" FontStyle="Italic">
     <Properties><BasedOn type="object">CharacterStyle/$ID/[No character style]</BasedOn></Properties>
   </CharacterStyle>
   ```
   Then split source text on `_word_` regex and emit alternating `<CharacterStyleRange AppliedCharacterStyle="CharacterStyle/Italic">` blocks.

8. **String-template XML emission only.** `xml.etree.ElementTree` alphabetizes namespaces and clobbers `idPkg:Spread`. Reuse the patterns from `scripts/layout_book.py` (string concatenation).

9. **ZIP layout.** `mimetype` first, uncompressed (`ZIP_STORED`). Everything else `ZIP_DEFLATED`. Keep `Spread_u51f6.xml` (title page) verbatim from template.

10. **`designmap.xml` patches.** Update three things: rewrite the `<idPkg:Spread src=...>` block, insert new `<idPkg:Story src=...>` refs before the existing last one, append new story IDs to the `StoryList=` attribute (before the terminating `ub1`). Update `<Section Length=...>` and `AlternateLayoutLength` to the new total page count.

## Calibration

- **Words per frame:** 240 (gives ~500-page final book for 121k-word P&P). Earlier sessions guessed 117 and produced a 1221-page output — a 3x over-allocation that the user spotted immediately. Real BBB Baskervvol 9.75pt density in a 225pt column is ~290 wpf; 240 leaves ~20% safety margin.
- **Chapter number font size:** Tuned per book by the human, not the script. Double-digit chapters (e.g. "22", "66") must fit without overflowing the number frame. If the template ships a value that overflows, the human edits `ParagraphStyle/Chapter Numbers` PointSize in `Resources/Styles.xml` — the script does not auto-fit.

## Workflow (every IDML run)

### Before generating

Spawn an **Explore agent** to read the current template state, even if you think you remember it. Templates drift between sessions when Matt or the user tunes them.

```
Explore agent prompt: "Unzip /Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice-finals/book_template.idml to /tmp/. Report:
1. Resources/Styles.xml — all paragraph styles by name + key properties (PointSize, Leading, FirstLineIndent). Confirm Basic Paragraph BBB, Chapter Header, Chapter Numbers exist with expected values.
2. MasterSpread_ue8dd.xml — frame IDs and their ItemTransform + path anchors for the chapter number frame (ue977) and label frame (ue990). Compute net spread coords (transform + anchor).
3. Master B placeholder story contents — confirm ue994 has 'CHAPTER' literal and ue97a has the number placeholder.
4. Whether CharacterStyle/Italic exists already.
Report in under 400 words."
```

Update the geometry constants in `build_opener_spread()` if Matt has retuned Master B.

### During generation

Run `python3 scripts/layout_book.py` end-to-end. The in-script `validate()` runs four audits and exits nonzero on failure:
- 61 chapter openers, all on recto pages (odd `Name=`)
- `CharacterStyle/Italic` present in `Resources/Styles.xml`
- Per-chapter word parity (`<Content>` text count == source word count, using consistent segment-based counting)
- Per-chapter italic parity (`CharacterStyle/Italic` range count == `_word_` marker count in source)

### After generation, before claiming done

1. **Spawn a structural-audit agent** to re-open the emitted IDML and verify deeper invariants the in-script validate misses:
   ```
   general-purpose agent prompt: "Open /Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice-finals/all_male.idml. Verify:
   1. Every spread referenced in designmap.xml exists in the ZIP.
   2. Every Story ID in StoryList= has a corresponding Stories/Story_*.xml file.
   3. Master B's placeholder stories (ue94b, ue97a, ue993, ue9b5, ue9ce, ue9e7, uea00) and Master A's (u637e, u5ff1, u600a, u6023, u603d) are all present and non-empty (or empty-but-well-formed).
   4. Pick 3 random body Story_<gid>.xml files and confirm <Content> + <CharacterStyleRange> structure is well-formed XML.
   5. For 3 random chapter opener spreads, confirm OverrideList suppresses MB_FRAME_BODY (ue961 n) and overrides MB_FRAME_NUM + MB_FRAME_LABEL with concrete frame IDs that appear as <TextFrame Self=...> children of the spread.
   Report findings in under 300 words."
   ```

2. **Call `advisor()`**. It caught the page-inflation problem and the word-count parity bug in past sessions. Do not skip this.

3. **Print a visual checklist for the human** (do not claim "done" until they confirm). Required items:
   - Open the IDML in InDesign 2026.
   - Confirm page 1 = title spread untouched.
   - Spot-check chapter 1 opener recto: "PRIDE & PREJUDICE" running head, "CHAPTER" label, large PicNic numeral. No body text on this page.
   - Spot-check next page (verso after opener): body text starts here with "It is a truth universally acknowledged..." (or the variant's equivalent).
   - Spot-check a double-digit chapter opener (e.g. chapter 22, chapter 66): confirm the number fits without overflow. If it overflows, the human re-tunes `ParagraphStyle/Chapter Numbers` PointSize.
   - Confirm 61 chapter openers all land on rectos.
   - Spot-check chapter 35 (Darcy's letter — italic-heavy passage) for italic rendering.

## Iteration discipline

- Calibration constants are **assumptions until verified**. The 117 → 240 wpf change was a 2.6× difference caught only because the user saw 1221 pages. Always print page count after generation and sanity-check against expected (~500 for P&P-length books).
- Layout choices that "look right" on a single chapter may break on others. Test chapter 1 visually (short), chapter 22 (double-digit number), chapter 35 (italic-heavy Darcy letter), and the longest chapter. Don't ship after only checking chapter 1.
- When the user reports the layout is wrong, do not iterate on geometry without reading the relevant master XML again. Trust the master template as source of truth for frame positions — do not invent layouts.

## Propagating to other variants

Once the human has trimmed blank pages from `all_male.idml` and tuned styles, run the same script over the other three variants (`all_female.json`, `nonbinary.json`, `gender_swap.json`) to produce matching IDMLs. Or use `scripts/apply_styles.py` (legacy reference) which propagates only `Resources/` and `MasterSpreads/` from a tuned source IDML to peers — useful when the human has only edited styles, not content.
