# Plan: User-Controlled Character Selection CLI

Based on deep codebase analysis, here's the **leanest approach** to implement user-controlled character-level name and gender selection:

## 🎯 Core Strategy 

**Add an `--interactive` mode** that leverages existing architecture:

1. **Extend CLI (`regender_cli.py`)** - Add `--interactive` flag that triggers character selection workflow
2. **Create interactive character selector** - Simple terminal UI to present characters and collect user choices  
3. **Use existing `TransformType.CUSTOM`** - Pass user selections as custom character mappings
4. **Leverage existing transformation pipeline** - No changes needed to core services

## 🛠️ Implementation Steps

### 1. CLI Extension (5 minutes)
- Add `--interactive` argument to `regender_cli.py`
- Modify `process_book()` to handle interactive mode
- Route to new `interactive_character_selection()` function

### 2. Interactive Character Selector (15 minutes) 
```python
def interactive_character_selection(characters: CharacterAnalysis) -> Dict:
    # Display characters with current gender/names
    # Allow user to:
    #   - Select which characters to transform  
    #   - Choose new gender for each
    #   - Optionally set new names
    # Return custom transformation mappings
```

### 3. Integration with Transform Service (5 minutes)
- Pass user selections to `TransformService` as `TransformType.CUSTOM`
- Use existing `_create_context()` method with user mappings
- No changes to core transformation logic needed

## 🧪 Testing Strategy

### Phase 1: Quick Validation (30 minutes)
- Test with `pg1080-A_Modest_Proposal.json` (238 lines, 14 characters)
- Verify character analysis → user selection → transformation pipeline
- Check that user selections are correctly applied

### Phase 2: Broader Testing (30 minutes)  
- Test with `pg1342-Pride_and_Prejudice.json` (larger cast)
- Validate edge cases (unknown gender, multiple aliases)
- Ensure quality control works with custom mappings

## 🚀 Key Advantages

- **Minimal code changes** - Reuses 90% of existing architecture
- **Fast implementation** - ~25 minutes coding + 60 minutes testing  
- **No breaking changes** - All existing functionality preserved
- **Leverages existing LLM integration** - Character analysis already works
- **Uses proven patterns** - Follows existing CLI and service patterns

## 📁 Files to Modify

1. `regender_cli.py` - Add `--interactive` flag and handler
2. New: `src/interactive_selector.py` - Character selection UI  
3. Minimal changes to `src/services/transform_service.py` - Handle custom mappings

## 🔍 Key Findings from Codebase Analysis

### Existing Architecture Strengths
- **Service-oriented design** - Clean separation between character analysis, transformation, and quality services
- **Character model is rich** - Already supports names, aliases, genders, pronouns, importance levels
- **Transformation model supports custom types** - `TransformType.CUSTOM` exists but unused
- **CLI already has good patterns** - Uses argparse, has interactive precedent in `interactive_transform.py`

### Integration Points Identified
- **Character Analysis** - `CharacterService.process_async()` returns `CharacterAnalysis` with all character data
- **Transform Service** - `_create_context()` method can accept custom character mappings
- **CLI Flow** - `process_book()` function in `regender_cli.py` orchestrates the pipeline
- **Existing JSON Data** - Character analysis files already exist (e.g., `pg1080-A_Modest_Proposal-characters.json`)

### Sample Character Data Structure
```json
{
  "name": "Elizabeth Bennet",
  "gender": "female", 
  "pronouns": {"subject": "she", "object": "her", "possessive": "her"},
  "titles": ["Miss"],
  "aliases": ["Lizzy", "Eliza"],
  "importance": "main",
  "confidence": 1.0
}
```

## ⚡ Implementation Details

### CLI Interface Design
```bash
# New interactive mode
python regender_cli.py books/texts/pride_and_prejudice.txt --interactive

# Would show:
# 1. Run character analysis
# 2. Present character list with current genders
# 3. Allow user to select characters and new genders/names  
# 4. Apply custom transformation
# 5. Save result
```

### User Interaction Flow
1. **Character Analysis**: Auto-run character analysis if needed
2. **Character Display**: Show characters grouped by importance (main, supporting, minor)
3. **Selection Interface**: Simple numbered menu for character selection
4. **Transformation Options**: For each selected character:
   - Keep current name or enter new name
   - Select new gender (male/female/nonbinary/unchanged)
5. **Preview & Confirm**: Show transformation summary before applying
6. **Apply & Save**: Run transformation with custom mappings

This approach gets you a working interactive character selector in ~2 hours total, perfect for your jam session with Bill!