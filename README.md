# Regender

![Four editions of Pride and Prejudice: swapped, all male, all female and nonbinary](docs/images/regender-covers.jpg)

Regender changes the gender of every character in a public domain book, so you can read an old story from a different position. Every other word stays the author's.

The first title is Jane Austen's *Pride and Prejudice*, in four versions. In one, every character's gender is swapped, so Mr. Bennet becomes Mrs. Bennet. In the others, the whole cast is male, female or nonbinary. They're printed books, with cover illustrations by Raman Djafari and book design by Matt Bucknall, and you can find them at **[regender.xyz](https://regender.xyz)**.

This repository is the software that made them. It's free and open source, so you can make your own.

## The first line, four ways

> It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

| Version | |
|---|---|
| **Swapped** | ...a single woman in possession of a good fortune, must be in want of a husband. |
| **All male** | ...a single man in possession of a good fortune, must be in want of a husband. |
| **All female** | ...a single woman in possession of a good fortune, must be in want of a wife. |
| **Nonbinary** | ...a single person in possession of a good fortune, must be in want of a spouse. |

Gender in a novel decides who inherits, who proposes and who gets to speak. Change it everywhere at once and some scenes collapse while others gain tension. The original starts to look built, which it was.

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

## How well it works

A find-and-replace breaks on the first "her", which can mean "him" or "his". Regender has a model read each passage in context, then runs a fixed rule pass over the result, so no gendered word survives a model call that failed. A quality check reads every chapter and says plainly when it couldn't check something.

All four editions of *Pride and Prejudice* reached 99.8% coverage or better before they went to print. Reading the laid-out proofs still turned up mistakes no check could see, like Project Gutenberg's notes to a typesetter arriving on the page as text. Each one became a test. There are about 1,300.

The nonbinary version needs a person at the end. It lists the words it couldn't settle by rule, and you decide each one.

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
- Book design: Matt Bucknall
- Typography: Bye Bye Binary
- Engineering: Bill Barnes
- Agent: Claude

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

Use it, fork it, run it on another book. Copyleft is deliberate: if you distribute a modified version, it carries the same licence and the same credit, and its source stays available. Nobody gets to close it.
