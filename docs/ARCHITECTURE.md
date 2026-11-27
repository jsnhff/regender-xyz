# How it fits together

Regender turns a plain-text book into a regendered edition in six steps. Each step writes what it decided into the run folder beside the book, so a run can be read afterwards and a decision can be disputed.

```
text file → parse → cast → names → transform → QC → rulings and export
```

`Application.process_book` in `src/app.py` runs the steps in order. The command line (`regender_cli.py`) and the app (`src/cli/tui.py`) both call it. The Mac app in `electron/` runs the same Python in a window.

## 1. Parse

`src/parsers/` and `ParserService` turn the text into a `Book` of chapters and paragraphs. Project Gutenberg front and back matter is removed. Plays have their own parser (`play.py`). Paragraphs are kept one to one with the source from here on, which is what lets every later step compare a paragraph with the one it came from.

## 2. Cast

`CharacterService` has a model read the book in chunks and list the characters: name, gender, aliases, titles. Entries for the same person are merged.

Written: `characters.json`.

In the app, this is where a person reviews the cast.

## 3. Names

`NameEngine` (`src/services/name_engine.py`) chooses every rename once, before any chapter is transformed, so the whole book agrees. A model proposes; code checks each proposal against the cast and refuses the ones that would merge two people, invent a name or drop one. Names a person supplied win.

For a gender swap, `character_state.py` works out which men are married when the book opens and where each one marries, from the titles the book itself prints. "Mr." does not say; "Miss" and "Mrs." do, so the swap has to know.

The finished map is audited before the transform starts.

Written: `name_map_proposed.json`, `name_report.json`, and `name_map_problems.json` if the audit found any.

## 4. Transform

`TransformService` sends each chapter to the model in batches of paragraphs, each paragraph under a `[[Pn]]` marker so the reply can be matched back exactly. Chapters run in parallel.

After the model, two deterministic passes run over each paragraph:

- the name map, resolved at that paragraph, for any name the model left alone;
- the term map, a set of rules for words whose answer never varies.

A batch that fails is retried paragraph by paragraph, then in groups of sentences. Text that no call succeeded for keeps its original wording and is recorded, and the run reports the chapter as untransformed.

Written: `<transform>.json`, `<transform>.txt`, `name_map.json` (the map as applied), `substitutions.json` and `substitutions_to_review.json`.

## 5. QC

`QCService` compares the transformed book with its source, chapter by chapter. No model is involved. Findings are graded by what can be done about them:

- `auto_fixable`: the safety net would still change this;
- `needs_review`: a gendered word the rules will not guess at;
- `structural`: counts that no longer match the source, or a character called a name nobody chose.

Written: `<transform>_qc.json`. `scripts/qc_report.py` runs the same checks on any finished book.

## 6. Rulings and export

Some words cannot be settled by rule: a "sir" or "madam" spoken to someone, a "master" that may be a title or a teacher. `DecisionService` lists them for a person to rule on, and applies the rulings.

The app exports `.txt`, `.rtf` or `.json`.

## Providers

`src/providers/` has one class each for Anthropic, OpenAI and Ollama. They share one interface, `complete(messages)`, and each raises when a reply is cut off or declined so that part of an answer is never taken for the whole.

## Tests

`python -m pytest tests/` runs without an API key. The model is replaced by mocks, and several tests use a real cast of Pride and Prejudice saved in `tests/fixtures/`.
