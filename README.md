# Regender

Regender changes the gender of every character in a public domain book, so you can read an old story from a different position. Every other word stays true to the original story.

The first title and demo is Jane Austen's *Pride and Prejudice*, in four versions. In one, every character's gender is swapped, so Mr. Bennet becomes Mrs. Bennet. In the others, the whole cast is male, female or nonbinary. They're available in print in unlimited editions as print-on-demand, sold at cost to increase access. Gratitude to Raman Djafari for the incredible cover illustrations and to Matthew Bucknall for the book design. You can find them at **[regender.xyz](https://regender.xyz)**.

This repository contains the software used to make them. It's free and open source, so you can make your own. Enjoy and let me know what you make.

## The first line, four ways

> It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

| Version | |
|---|---|
| **Swapped** | ...a single woman in possession of a good fortune, must be in want of a husband. |
| **All male** | ...a single man in possession of a good fortune, must be in want of a husband. |
| **All female** | ...a single woman in possession of a good fortune, must be in want of a wife. |
| **Nonbinary** | ...a single person in possession of a good fortune, must be in want of a spouse. |

Gender in a novel decides who inherits, who proposes and who gets to speak. Change it everywhere at once and some scenes stop working while others get sharper. You can see how much of the plot was resting on it.

## Try it on a book

You need a public domain book as a plain text file (any [Project Gutenberg](https://www.gutenberg.org) book works) and one of these:

- an [Anthropic](https://console.anthropic.com/settings/keys) or [OpenAI](https://platform.openai.com/api-keys) API key, or
- [Ollama](https://ollama.com), which runs a model on your own computer for free.

The books were made with Anthropic's models, so that path is the most tested. If OpenAI or Ollama gives you trouble, please [open an issue](https://github.com/jsnhff/regender-xyz/issues).

The app walks you through setup the first time it opens.

**Mac app.** Download **Regender.dmg** from [Releases](https://github.com/jsnhff/regender-xyz/releases/latest), drag it to Applications and open it. Apple Silicon Macs only.

**Terminal, one line.** Needs Python 3.9 or later.

```bash
curl -fsSL https://raw.githubusercontent.com/jsnhff/regender-xyz/main/start.sh | bash
```

It installs into `~/regender-xyz`, in a Python environment of its own, and opens the app.

**From source.**

```bash
git clone https://github.com/jsnhff/regender-xyz.git
cd regender-xyz
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python regender_cli.py
```

The app asks for a book, a model and one of four transforms, then saves the result as `.txt`, `.rtf` or `.json`.

## The four transforms

| Name | What it does |
|---|---|
| `gender_swap` | Every character's gender is swapped. Elizabeth becomes a young man and Darcy a woman. |
| `all_male` | Every character becomes male. |
| `all_female` | Every character becomes female. |
| `nonbinary` | Every character becomes nonbinary, and gendered language goes neutral. |

Names change too. You see the name map and can edit it before anything runs.

## How it works

A find-and-replace breaks on the first "her", which can mean "him" or "his". Regender works in two layers instead.

Python does the deterministic part: finding the cast, matching a name across its spellings and titles, and applying a map of rules for the cases where the right answer never varies. A model reads each passage in context for everything the rules can't see. The rule pass then runs again over what the model returned, so no gendered word survives a model call that went wrong. That leaves a handful of words no rule or model can settle without your judgement.

The rest are editorial calls. Regender identifies them, brings them to you with some context, and asks for your decision. This happens before the transform runs. The software counts them, tells you where they are, and shows the mechanical readings of each. This keeps them from ending up in a printed book or PDF. Running `--estimate` reports the count without transforming anything if you want to check first.

Every word is either settled automatically or ruled on by you. This combo makes the transformation complete.

A quality check reads every chapter afterwards, grading what it finds: fixable by rule, needs a person, or a structural problem like a missing chapter. It says when it fails or wasn't able to check something. Every time I run it on a new book I find a new way to improve it. English is complex.

## Command line

```bash
# Swap the sample chapters that come with the repo
python regender_cli.py books/texts/pride-prejudice-sample.txt gender_swap

# Choose the new names yourself
python regender_cli.py books/texts/pride-prejudice-sample.txt all_male \
  --name-map '{"Elizabeth":"Elliot","Jane":"James"}'

# Count the decisions a nonbinary run will need, without running it
python regender_cli.py books/texts/pride-prejudice-sample.txt nonbinary --estimate
```

`python regender_cli.py --help` lists every option.

## For developers

```bash
pip install -r requirements.txt
python -m pytest
```

The tests run without an API key. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains how the parser, the cast analysis and the transform fit together. Issues and pull requests are welcome. A book that breaks the parser makes a good first issue.

## Credits

Made by [Jason Huff](https://jasonhuff.info), Los Angeles, 2026.

- Cover illustration: [Raman Djafari](https://ramandjafari.com)
- Book design: Matthew Bucknall
- Engineering: William Barnes
- Type set in BBB Baskervvol, a post-binary fork of Baskervville by [Bye Bye Binary](https://typotheque.byebyebinary.space) et al.; BBB Herthey Futural, Clara Sambot and Laure Giletti's fork of Paul Bernhard's Hershey Futural; and PicNic by Mariel Nils
- Text transformed by claude-opus-4-5-20251101, September 13, 2026

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

Use it, fork it, run it on another book. Copyleft is deliberate: if you distribute a modified version, it carries the same licence and the same credit, and its source stays available. Nobody gets to close it.
