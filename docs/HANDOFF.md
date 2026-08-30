# Handoff — transform correctness work

_Branch `claude/repo-state-5ylut4`. `main` is untouched, nothing is merged, no PR
is open for this branch._

## Where this started

A reader (Carly) found a sentence in the printed gender-swap prototype where half
of a gendered pair had changed and half had not. She later flagged a second thing
on page 19: a paragraph indent arriving mid-sentence.

Both turned out to be real bugs, and chasing them turned up several more.

## The honest status

**No real end-to-end test has happened.** This environment has no LLM API key and
the network policy blocks gutenberg.org, so there is no live model run and no full
book text — only the 6-chapter sample in `books/texts/`.

What was done instead was to stand in for the model: writing a gender-swapped
Chapter 1 by hand and replaying it through the real pipeline. That does exercise
batching, the prompt, marker parsing, the retry path and the safety net. It does
**not** prove the output prose is good, because the same author wrote the model
output, the transform, and the QC that checks both. A green report across those
three mostly demonstrates that they agree with each other.

The one piece that pushes back on this is `tests/test_qc_sensitivity.py`, which is
adversarial against QC — it injects faults and requires each to be caught. Its
clean baseline is still a judgment call.

Treat every "100%" in the artifact and in commit messages with that in mind.

## What is on the branch

Oldest first. `git log --oneline main..HEAD`.

### Mechanical, and about as provable as this gets

- **`873dd26` term map applied in one simultaneous pass.** It ran as a sequence of
  independent regex passes, so for a bidirectional map `mother→father` was
  followed by `father→mother` and the second pass rewrote the first. All 56 pairs
  collapsed onto one gender, and correct model output was reverted. This is the
  bug behind Carly's sentence.
- **`eef00b6` batch responses carry `[[Pn]]` markers.** The old protocol split on
  blank lines and, on any miscount, padded with empty strings or truncated —
  deleting paragraphs and shifting the rest of the chapter into the wrong slots.
- **`4f0b5d9` parser rejoins sentences split by an illustration plate.** This is
  the page-19 indent.
- **`d50baaf` `TimeoutError` no longer shadows the builtin,** so provider timeouts
  stop being logged as generic internal errors. Also clears the ruff backlog.
- **`43ba262` `ruff format` across the repo.** Formatting only.

### Judgment calls that want a second opinion

- **The ambiguous-`her` heuristic** (`_CONTEXTUAL_PRONOUNS`, `_ADVERBIAL_AFTER` in
  `src/services/transform_service.py`). "her" before a content word is treated as
  possessive. Correct for all 44 such cases in the sample text, and it will be
  wrong sometimes — "he saw her walking" becomes "she saw his walking". Pinned
  deliberately in `test_object_complement_is_a_known_limitation` so the trade-off
  stays visible. The conservative alternative is to leave these for review, which
  costs roughly 450 manual items across a full book.
- **The prompt rewrite** (`4a80c6c`). The rules were being interpolated as a raw
  Python dict with no plain statement of the task, and every transform was told to
  "simplify to the target gender only" for paired terms — right for all_male and
  all_female, destructive for a swap. Rewritten and pinned in `tests/test_prompt.py`.
  Worth reading the rendered output and deciding if it says what you want.
- **CI lint is now blocking** (`d0b37e7`). Fine while the repo is clean; it will
  stop a PR on a formatting nit.
- **PR #12 was merged into this branch** (`9c7d08a`, `d7a55d7`) — bounded provider
  retries and the async mock fix. **The PR is still open on GitHub.** Close it or
  supersede it.

## Open questions for tomorrow

1. **Does the branch land as-is, in pieces, or not at all?** Reading the diff is
   the next step, not more work from this side.
2. **The `her` heuristic** — accept the trade-off, or revert to conservative and
   take the review queue?
3. **PR #12** — close as merged here, or keep separate?

## Blocked on

| Need | Why | Unblocks |
|---|---|---|
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | No live model run is possible | A genuine 61-chapter transform |
| gutenberg.org in the network policy, **or** the full `pg1342.txt` committed | Only a 6-chapter sample is in the repo | Book-wide deterministic and parser checks, no model needed |
| The printed edition's `source.json` + `gender_swap.json` (+ `name_map.json`) | Not in the repo | Tells us exactly what is wrong with the copy Carly is holding, and `--repair` can fix most of it with no model calls |

## Important if any of this ships

The illustration-plate fix **changes paragraph structure**, so the next PDF needs a
**re-parse from source**, not a repair of the existing JSON. Chapter 3 of the
sample goes from 21 paragraphs to its correct 20. Every title in
`.claude/bugs.md` is an illustrated edition and likely carries the same defect.

## Running things

```bash
pip install -r requirements.txt
python -m pytest tests/ -q                 # 152 tests, no API key needed

# QC a transform against its source, chapter by chapter
python scripts/qc_report.py source.json swap.json gender_swap
python scripts/qc_report.py source.json swap.json gender_swap --name-map name_map.json
python scripts/qc_report.py source.json swap.json gender_swap --fail-on auto_fixable
python scripts/qc_report.py source.json swap.json gender_swap --repair fixed.json
```

Findings are graded `auto_fixable` (the safety net would still change this, so the
text predates the fix), `needs_review` (a gendered word the net will not guess at),
and `structural` (counts, length drift, sentences split across paragraphs).

To run the pipeline with no API key, `src/providers/cassette.py` records the
prompts a run generates so they can be answered by any model and replayed. See
its module docstring.

## Where things live

| | |
|---|---|
| Transform + safety net | `src/services/transform_service.py` |
| QC | `src/services/qc_service.py`, CLI at `scripts/qc_report.py` |
| Offline provider | `src/providers/cassette.py` |
| Parser fix | `src/parsers/gutenberg.py` (`_clean_lines`) |
| Tests | `tests/test_transform_terms.py`, `test_qc_service.py`, `test_qc_sensitivity.py`, `test_batch_protocol.py`, `test_batch_recovery.py`, `test_prompt.py`, `test_cassette.py` |

Write-up with the mechanisms and diagrams:
https://claude.ai/code/artifact/ef2829c6-42cc-4647-b370-7cbc730b13ff
