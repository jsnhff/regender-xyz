# Interactive Character Selection Usage

## 🎯 Quick Start

The interactive character selection feature allows you to manually choose which characters to transform and how to transform them.

### Basic Usage

```bash
# Interactive mode with existing character analysis
python regender_cli.py books/json/pg1080-A_Modest_Proposal.json --interactive

# Or use the 'custom' transform type directly  
python regender_cli.py books/json/pg1080-A_Modest_Proposal.json custom
```

### Prerequisites

1. **JSON format book**: Convert text to JSON first if needed:
   ```bash
   python regender_cli.py books/texts/my_book.txt parse_only
   ```

2. **Character analysis**: Run character analysis if no `-characters.json` file exists:
   ```bash
   python regender_cli.py books/json/my_book.json character_analysis
   ```

## 🎭 Interactive Workflow

### Step 1: Character Display
The system shows all characters grouped by importance:

```
📚 MAIN CHARACTERS (2):
  1. Narrator (male)
  2. The Narrator (male)

👥 SUPPORTING CHARACTERS (2):  
  3. American acquaintance (male)
  4. Very worthy person (male)

🎭 MINOR CHARACTERS (10):
  5. Dr. Jonathan Swift (male)
  6. The Pretender (male)
  ...
```

### Step 2: Character Selection
Choose which characters to transform:

- **Select specific characters**: `1 3 5` (characters 1, 3, and 5)
- **Select all characters**: `all`

### Step 3: Configure Each Character
For each selected character:

1. **Choose new gender**:
   - `1` = male
   - `2` = female  
   - `3` = nonbinary
   - `4` = keep unchanged

2. **Optional name change**: Enter new name or press Enter to keep current name

### Step 4: Review & Apply
The system shows your configuration and applies the custom transformation.

## 📝 Example Session

```
🎭 INTERACTIVE CHARACTER SELECTION
Found 14 characters in the book:

📚 MAIN CHARACTERS (2):
  1. Narrator (male)
  2. The Narrator (male)

Select characters to transform: 1 12 13
Configuring 3 character(s):

--- Narrator (currently: male) ---
Select new gender: 2
New name (press Enter to keep 'Narrator'): Eleanor

--- Plump girl of fifteen (currently: female) ---  
Select new gender: 1
New name: Young man of fifteen

--- Narrator's Wife (currently: female) ---
Select new gender: 4
New name: [Enter]

✅ Configured 3 character mappings.
```

## 🔧 Current Status

**✅ Implemented:**
- CLI arguments (`--interactive`, `custom` transform type)
- Character display and selection interface
- Gender and name configuration per character
- Integration with existing character analysis files

**🚧 Next Steps:**
- Full transformation pipeline integration
- LLM provider setup for character analysis
- Output file generation with custom mappings

## 🎪 Demo

Run the demonstration:
```bash
python test_interactive.py
```

This shows how the interactive selection works with the A Modest Proposal sample.