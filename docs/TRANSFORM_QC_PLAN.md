# Bringing the other three transforms up to the gender_swap standard

`gender_swap` is done: 61/61 chapters, 0 findings, verified by reading as well
as by the tool. Evidence in
`books/output/pride-and-prejudice-finals/press_ready_files_82926/`.

This is what it took, and what the same treatment costs for the other three.

## Where the other three stand

Measured 2026-08-29 against a correct 61-chapter parse, with the possessive fix
in place. No model calls — `scripts/qc_report.py` only.

| variant | auto-fixable | needs review | structural | coverage | worst chapter |
|---|---|---|---|---|---|
| gender_swap *(before)* | 1067 | 1199 | 86 | 89.0% | ch35 — 285 |
| gender_swap *(now)* | **0** | **0** | **0** | **100%** | — |
| all_male | 33 | 29 | 89 | 99.4% | ch35 — 60 |
| all_female | 103 | 91 | 86 | 97.6% | ch35 — 188 |
| nonbinary | 305 | 27 | 86 | 99.7% | ch45 — 37 |

Two things to read off that table.

**The structural damage is identical everywhere** — the same 8 split paragraphs
plus ~80 length drifts, in all four. It is inherited from the parse, so one fix
serves all four, and none of them can be trusted until it is applied: while the
structure is wrong, QC compares paragraph *n* to the wrong source paragraph and
passes anyway. That is exactly how 31 defects hid behind a green report in the
swap.

**The other three are an order of magnitude cleaner than the swap was.** The
swap is bidirectional, so it alone suffered the term-map collapse where
`mother→father` was undone by `father→mother`. `all_male` at 33 auto-fixable is
close to finished.

`nonbinary`'s 305 are almost all safety-net rewrites (they/them verb agreement)
with only 27 needing review — mechanical, not editorial.

Chapter 35, Darcy's letter, is the worst chapter in three of four. It is the
long-paragraph failure zone; check it first, every time.

## The procedure, in order

Order matters. Steps 1–2 before 3, or the QC lies to you.

1. **Re-parse from source and count chapters.** Must be 61. The JSON committed
   at `books/json/pg1342-*.json` is a stale 49-chapter parse — the Roman-numeral
   bug dropped exactly 12. Do not use it.

2. **Align structure to the source.** Merge the 8 illustration-plate splits;
   in ch61 the extra paragraph is the publisher's colophon and is deleted, not
   merged. Choose per paragraph between merge and delete by whichever gives the
   lower total word-count difference against the source — a first-divergence
   heuristic picks the wrong seam in ch46, ch48 and ch61.

3. **Repair**: `python scripts/qc_report.py source.json v.json TYPE --repair out.json`.
   No model calls.

4. **Verify independently of the tool.** This is the part that matters; the
   tool and the transform share an author, so their agreement proves little.
   - *Token balance.* For a swap, every gendered pair mirrors. For `all_male`
     and `all_female` it is one-directional: the losing gender's counts go to
     zero. A pair that is short on one side and long on the other is a class of
     miss, not noise — that asymmetry is what exposed the possessive bug while
     the tool reported clean.
   - *Honorific parity*, paragraph by paragraph, against the edition's
     convention. Expect a handful of legitimate disambiguation insertions.
   - *Conjoined honorifics*: `Mr. and Mrs. X`. The LLM dropped one in ch46 of
     the swap, collapsing a couple into one person.
   - *Read*: opening, ending, every repaired seam, ch35, and the letters
     (ch13, 48, 57).

5. **Every defect found becomes a test** before moving on. See
   `TestPossessives` and `TestProtectedPhrases` in `tests/test_transform_terms.py`.

## Per-variant expectations

**all_male / all_female** — unidirectional, so the residual mask matters less,
but the possessive boundary bug hit them just as hard; re-run after the fix
before judging. `all_female` at 188 findings in ch35 is the known long-paragraph
possessive failure (`him temper` for `his temper`). `all_male` has 3 extra
structural findings the others lack — look at those before assuming they match.

**nonbinary** — different failure mode. Verb agreement after singular *they*
("they was"), `Mx.` honorifics, and gendered kinship with no neutral equivalent.
The 2 `pair_gender` findings are unique to it. The May print carried 371
honorific residues; that work is on `worktree-transform-hardening` and should be
merged first (see below).

## Not gender defects, but they must not reach print

Identical in the source parse, so they affect all four:

- straight quotes throughout (source is curly) — `worktree-smart-quotes-script`
- 18 `/* NIND … */` layout markers in 9 paragraphs
- 467 `--` wanting em-dashes, 158 multi-space runs
- `src/services/text_export_service.py:248` calls `self.process_async`, which
  does not exist — `export_to_file` raises. The text export path is broken.

## Branches

Three lines of work solve overlapping problems and have diverged.

- `integration/swap-100` *(this work)* — possessive fix, protected phrases,
  version-independent timeout classification, 162 tests. Built on
  `claude/repo-state-5ylut4`.
- `worktree-transform-hardening` — 9 commits, all four variants passing its own
  gates on a full P&P run (2026-08-15). Has `name_engine.py` (decide-once name
  map, collision detection, title+name atomicity) and `qc_gates.py`, neither of
  which exists on the repo-state line. It also fixes the `parse_only` CLI crash
  that `integration/swap-100` still has.
- `claude/testing-production-improvements-CrJlx` — CI plus provider retries,
  already merged into the repo-state line as PR #12. **PR #12 is still open on
  GitHub**; close it.

**Recommended order.** Land `integration/swap-100` first — it is verified
end-to-end against a real printed book, which nothing else here is. Then port
`name_engine.py` from `worktree-transform-hardening` on top: it is the piece
this work does not have, and it is what fixes `Lord Catherine` keeping a female
given name, and `Colonella`-style rank inflection. Take `qc_gates.py`'s
name-consistency gate too; it catches merges like Sir William Lucas being
absorbed into "Lady Lucas", which nothing on this branch would notice.
