# Regender

Regender changes the gender of every character in a public domain book, so you can read an old story from a different position. Every other word stays the author's.

The first title is Jane Austen's *Pride and Prejudice*, in four versions. In one, every character's gender is swapped, so Mr. Bennet becomes Mrs. Bennet. In the others, the whole cast is male, female or nonbinary. They're printed books, with cover illustrations by Raman Djafari and book design by Matthew Bucknall, and you can find them at **[regender.xyz](https://regender.xyz)**.

This repository is the software that made them. It's free and open source, so you can make your own.

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

You need a book as a plain text file (any [Project Gutenberg](https://www.gutenberg.org) book works) and one of these:

- an [Anthropic](https://console.anthropic.com/settings/keys) or [OpenAI](https://platform.openai.com/api-keys) API key, or
- [Ollama](https://ollama.com), which runs a model on your own computer for free.

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

Python does the deterministic part: finding the cast, matching a name across its spellings and titles, and applying a map of rules for the cases where the right answer never varies. A model reads each passage in context for everything the rules can't see. The rule pass then runs again over what the model returned, so no gendered word survives a model call that went wrong.

That leaves a handful of words no rule and no model should settle on your behalf. English has no neutral "sir" or "madam"; they mark rank and distance rather than the speaker's sex, and every substitute says something the original didn't. "Master" is an employer, a teacher, a household head, and half of "his own master", and only the words beside it decide which. Some of those the rules do settle, so "music master" becomes "music teacher" without asking.

The rest are editorial calls, and Regender treats them as yours. Before the transform runs it counts them, tells you where they are and shows the mechanical readings of each, so you rule on them up front instead of finding them in a printed book. `--estimate` reports the count without running anything. The nonbinary transform needs the most rulings by a wide margin.

Every word is either settled automatically or ruled on by you, so a finished book has nothing left unresolved in it.

A quality check reads every chapter afterwards and grades what it finds: fixable by rule, needs a person, or a structural problem like a missing chapter. It says plainly when it couldn't check something. Reading the laid-out proofs still turned up mistakes no check could see, such as Project Gutenberg's notes to a typesetter arriving on the page as text. Each one became a test. There are about 1,300.

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
