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

## TODOs

### Completed
- [x] Fix OpenAI API JSON format compatibility issue
- [x] Improve pronoun consistency in gender transformations
- [x] Add post-processing validation for relationship possessives
- [x] Implement and test gender-neutral transformation
- [x] Fix pronoun validator patterns for neutral transformation

### Next Steps
- [ ] Add support for custom prompts and instructions
- [ ] Implement batch processing for multiple files
- [ ] Add support for character relationship analysis
- [ ] Create visualization tools for character networks
- [ ] Improve handling of complex literary devices (metaphors, etc.)
- [ ] Add unit tests for core functionality
- [ ] Implement progress bars for long-running operations
- [ ] Add support for more output formats (EPUB, PDF, etc.)
- [ ] Create a configuration file for persistent settings
- [ ] Expand pronoun validator to handle more edge cases
- [ ] Add option to disable pronoun validation for performance
- [ ] Create a simple web interface for the tool
- [ ] Develop visualizations for comparing original and transformed texts
- [ ] Implement comparative analysis between different transformation types

## Benchmark Test Cases

The following test cases represent increasing levels of complexity for evaluating the system's performance, focusing on Pride and Prejudice and other public domain works:

### Level 1: Basic Transformation
- [x] Pride and Prejudice Chapter 1 (feminine transformation)
- [x] Pride and Prejudice Chapter 1 (neutral transformation)
- [ ] Pride and Prejudice Chapter 1 (masculine transformation)

### Level 2: Intermediate Complexity
- [ ] Pride and Prejudice Chapters 2-3 (all transformation types)
- [ ] Pride and Prejudice dialogue-heavy scene
- [ ] Pride and Prejudice character introduction scene

### Level 3: Advanced Challenges
- [ ] Pride and Prejudice full chapter with multiple characters and relationships
- [ ] Pride and Prejudice ball scene (complex social interactions)
- [ ] Pride and Prejudice proposal scene (emotional content)

### Level 4: Extended Tests
- [ ] Pride and Prejudice Volume 1 (multiple chapters)
- [ ] Complete Pride and Prejudice novel
- [ ] Jane Austen's Emma (first chapter)

### Level 5: Comprehensive Tests (Project Gutenberg Works)
- [ ] Charles Dickens' A Tale of Two Cities (selected chapters)
- [ ] Charlotte Brontë's Jane Eyre (selected chapters)
- [ ] Mary Shelley's Frankenstein (selected chapters)
