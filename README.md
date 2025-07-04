# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature.

## Overview

This tool uses AI to identify characters in text and transform gender representation while preserving narrative coherence. It can perform character analysis, gender transformation, or both in a pipeline.

## Features

- **Character Analysis**: Identify characters, their gender, and mentions in text
- **Gender Transformation**: Transform text using different gender representations
  - Feminine transformation (male → female)
  - Masculine transformation (female → male)
  - Gender-neutral transformation
- **Verification**: Check for missed transformations
- **Simple CLI Interface**: Easy-to-use command-line interface

## Requirements

- Python 3.9+
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)
- **Recommended Model:** GPT-4.1 ChatGPT (1 million token context window, 32,768 token output limit)
  - See [GPT-4.1 Prompting Guide](https://cookbook.openai.com/examples/gpt4-1_prompting_guide) for best practices
  - Check [OpenAI's official announcements](https://openai.com/) for the most current specifications

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz

# Install dependencies
pip install openai

# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key'
```

## Usage

### Character Analysis

Analyze a text file to identify characters and their mentions:

```bash
python regender_cli.py analyze path/to/your/text.txt
```

Options:
- `-o, --output`: Specify output file for analysis results (default: input_file.analysis.json)

### Gender Transformation

Transform gender representation in a text file:

```bash
python regender_cli.py transform path/to/your/text.txt --type feminine
```

Options:
- `-t, --type`: Type of transformation to apply (feminine, masculine, neutral)
- `-o, --output`: Specify output file for transformed text

### Full Pipeline

Run both analysis and transformation in one command:

```bash
python regender_cli.py pipeline path/to/your/text.txt --type feminine
```

With GPT-4.1's large context window, you can process the full text of a novel (up to 1 million tokens) in a single call, as long as the output does not exceed 32,768 tokens.
- **Recommended Model:** GPT-4.1 ChatGPT (1M token context window, ~36K output token limit)
  - See [OpenAI API documentation](https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo) for current specs and limits.

Options:
- `-t, --type`: Type of transformation to apply (feminine, masculine, neutral)
- `-o, --output`: Specify output file for transformed text

## Examples

```bash
# Analyze Pride and Prejudice
python regender_cli.py analyze pride_and_prejudice_chapter_1_full.txt

# Transform to feminine gender representation
python regender_cli.py transform pride_and_prejudice_chapter_1_full.txt -t feminine

# Run full pipeline with gender-neutral transformation
python regender_cli.py pipeline pride_and_prejudice_chapter_1_full.txt -t neutral -o output/neutral_pride.txt
```

## Project Structure

- `regender_cli.py`: Main CLI entry point
- `analyze_characters.py`: Character analysis module
- `gender_transform.py`: Gender transformation module

## License

MIT

## Roadmap & Milestones

### Release 1: Complete Pride and Prejudice (Uniform Gender Swap)
- **Goal:** Transform the entire text of Pride and Prejudice by uniformly swapping all gendered language (pronouns, titles, etc.), with no character-specific choices. Keep it simple and consistent for the whole book.
- **Testing Plan:**
  - [x] Fix JSON parsing error in API response handling ("Unterminated string starting at: line 2 column 11")
  - [ ] Run gender swap transformation on the full novel text
  - [ ] Spot-check key scenes (opening, ball, proposal)
  - [ ] Validate pronoun, title, and relationship consistency throughout
  - [ ] Prepare print-ready manuscript for book design with Matt Bucknall
- **Critical Fixes Needed:**
  - [ ] Fix file writing logic to collect all transformed chunks in memory and write once at the end
  - [ ] Improve chapter boundary handling to ensure complete novel transformation
  - [ ] Implement full novel verification step using GPT-4.1's 1M token context window
  - [ ] Add validation to ensure consistent character representation throughout the novel
- **Milestone:** Print-ready version for book design collaboration

### Release 2: Website & Open Source Launch
- **Goal:** Launch a public website to open source the uniform gender-swapped version and sell print-on-demand copies.
- **Testing Plan:**
  - [ ] Website displays transformed book and project info
  - [ ] Print-on-demand integration works (test order flow)
  - [ ] Repo/documentation for public collaboration

### Release 3: Feature Improvements & Expansion
- **Goal:** Add advanced features and support for more books.
- **Testing Plan:**
  - [ ] Character-specific naming/gender choice
  - [ ] Interactive transformation options
  - [ ] Test on additional public domain works (Emma, Jane Eyre, etc.)
  - [ ] Enhanced validation, analytics, and visualization tools

---

## Completed

### Core Platform Development
- [x] **Third major rewrite:** Streamlined the codebase with a CLI-first focus and improved architecture ([77f59c0], [74505b6], [54d31a1])
- [x] Archived and cleaned up legacy versions, moving old code to `/archive` ([74505b6], [54d31a1])
- [x] Created project README and initial documentation ([5d623d5], [1ba486a])
- [x] Set up project structure and repository
- [x] Implemented main CLI entry point (`regender_cli.py`)
- [x] Implemented core character analysis and gender transformation modules
- [x] Added pronoun validator for transformation consistency
- [x] Added support for gender-neutral transformation with Mx. titles
- [x] Added post-processing validation for relationship possessives
- [x] Added colorful CLI visuals and animations
- [x] Implemented gender-themed animated spinners and progress bars
- [x] Fixed OpenAI API JSON format compatibility issue
- [x] Improved pronoun consistency in gender transformations
- [x] Fixed pronoun validator patterns for neutral transformation

### AI Chunking System (June 2025)
- [x] **Bulletproof AI Chunking:** Developed hybrid AI + Python chunking system achieving 100% text coverage
  - [x] Created `ai_chunking.py` module with guaranteed coverage for any Project Gutenberg book
  - [x] Implemented Python regex fallback when AI analysis unavailable
  - [x] Added automatic chapter pattern detection (Roman numerals, numbered chapters, titled chapters)
  - [x] Built size-aware chunking that adapts to book characteristics and respects 32k output limits
  - [x] Tested successfully on Pride & Prejudice (17 chunks) and Moby Dick (140 chunks)
- [x] **Consolidated Pipeline Testing:** Built unified test interface with command-line options
  - [x] Created `test_pipeline.py` with support for different transformation types
  - [x] Added `--save`, `--transform`, and `--all-books` flags for flexible testing
  - [x] Integrated AI chunking with character analysis and gender transformation pipeline
- [x] **Major Codebase Cleanup:** Prepared master branch for clean merge
  - [x] Removed 4,700+ unnecessary files (1.2M+ lines of code/dependencies)
  - [x] Deleted entire virtual environment directories that shouldn't be in git
  - [x] Enhanced .gitignore with comprehensive patterns for future cleanup prevention
  - [x] Preserved core functionality while removing all development cruft
- [x] **Competition-Ready Architecture:** Designed modular system for easy comparison with alternative approaches
  - [x] Separated AI chunking logic into standalone module for A/B testing
  - [x] Created clean APIs for swapping chunking implementations
  - [x] Focused transform logic purely on gender transformation, isolated from chunking concerns
