# Vocatives — plan, paused 2026-08-29 awaiting one decision

## Where the four variants stand

| variant | auto-fixable | structural | verb agreement | gendered residue | for review |
|---|---|---|---|---|---|
| gender_swap | 0 | 0 | — | 0 | 0 |
| all_male | 0 | 0 | — | 0 | 0 |
| all_female | 0 | 0 | — | 0 | 0 |
| nonbinary | 0 | 0 | 0 *(159 before)* | 0 | **31** |

All four books are in `books/output/pride-and-prejudice-finals/press_ready_files_82926/`.
The first three are finished. nonbinary is finished apart from the review list.

nonbinary's 31: **29 bare vocatives** (`sir` / `madam` / `ma'am`) and
**2 bare `master`** in a servant's speech, which carry no frame to read.

## The decision this is waiting on

A bare vocative has no neutral form in English. `Mx.` is a title and wants a
surname, so mapping it produced `"Indeed, Mx.,"` 18 times in the printed book.
The entries were removed; QC now reports the word instead of guessing.

Jason proposed a small transformation grammar rather than deletion — replace
what the vocative *does* (deference, formality) instead of dropping it:
adverb-fronting, modal + emphasis shift, imperative + `Pray`, opener reorder.

That is right, and `Pray` is a genuinely good period-neutral formality marker.
The objection is scope, not principle.

### What the 52 bare vocatives in the source actually are

| frame | n | % |
|---|---|---|
| clause-final tag — `…, I believe, sir.` | 19 | 37% |
| letter salutation — `Dear Sir,` | 14 | 27% |
| clause-medial — `You are very kind, sir, I am sure` | 10 | 19% |
| short reply — `Certainly, sir;` | 4 | 8% |
| imperative | 1 | 2% |
| opener — `Sir, you quite misunderstand…` | 1 | 2% |
| unclassified | 3 | 6% |

The grammar's four patterns cover ~29% of these. Its imperative and opener
patterns cover **one instance each**. The two largest frames are not in it.

### The proposal on the table

- **Delete — 29 cases** (clause-final + clause-medial). Dropping `, sir` from
  `…I believe, sir.` leaves correct Austen. Structure-preserving, invents
  nothing.
- **Name the addressee — 14 salutations.** A proper noun is unsafe mid-dialogue
  because it needs coreference, and a wrong name puts words in the wrong mouth.
  A letter's addressee is structurally explicit, so `Dear Sir,` →
  `Dear Mx. Bennet,` is determinable and idiomatic. This is the one place the
  proper-noun option is right.
- **The grammar — the remaining 6** (short replies, the imperative, the opener),
  where a substitution genuinely cannot carry the meaning. Small enough to
  eyeball each one.
- **3 unclassified** → look at them individually.

### Two risks worth keeping in view

**Reordering breaks what the QC relies on.** Length drift, paragraph alignment
and word-count parity at the repaired seams all assume structure-preserving
substitution. A clause reorder makes length-drift fire across the book and the
signal that caught the real corruptions is lost. Deletion and in-place
substitution keep it.

**Intensifier inflation and speaker register.** `Most certainly` fifty times
becomes a tic; Austen's `sir` works because it is unobtrusive. And `Pray` fits
Collins and Sir William but not Lydia or a servant — one grammar cannot see who
is speaking.

### Open question for Jason

For the 29 deletions: is losing the deference beat acceptable? In Austen it
carries class and irony — Collins's obsequiousness lives largely in these. That
is an editorial judgement about how the dialogue sounds, not a technical one.

The alternative is to keep `sir`/`madam` untouched and let them stand as the one
place English refuses to neutralise — arguably the honest choice for a book
about gender in language.

## Picking this up

1. Merge **#16** (coordination gate), then **#17** (sense rules, stacked on it).
2. Take the decision above, implement the three tiers, re-run nonbinary:
   `python3 scripts/qc_report.py <source> <transformed> nonbinary --repair out.json`
   Source parse and the aligner live in the evidence folder / `docs/TRANSFORM_QC_PLAN.md`.
3. Re-verify independently, not just on the QC verdict: token balance, honorific
   parity, conjoined pairs, and read the seams. The QC agreeing with the
   transform proves only that they agree.
4. All four then need a **re-flow from JSON** into InDesign, not a patch — the
   paragraph structure changed when the illustration splits were rejoined.
