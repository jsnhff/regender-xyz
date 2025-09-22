# Regender-XYZ System - Comprehensive Status & Continuation Guide

## Session Date: September 21, 2025

## Executive Summary
We've successfully built and refined a complete end-to-end pipeline for gender transformation of literature using LLMs. The system can analyze characters, apply various gender transformations, and output both JSON and print-ready ASCII text.

## What We Accomplished Today

### 1. Fixed Character Extraction (6 → 15+ characters)
- **Problem**: Only finding main characters, missing minor ones
- **Solution**: Enhanced prompt to explicitly request ALL characters including minor ones
- **Result**: Dr. Jekyll & Mr. Hyde went from 6 to 15 characters found

### 2. Improved Transformation Quality
- **Removed brittle hardcoded mappings** - Let LLM handle language naturally
- **Added character-aware context** - Provides character names and aliases to LLM
- **Result**: More accurate, context-aware transformations

### 3. Fixed Output Organization
- **Problem**: Multiple runs created separate folders for each phase
- **Solution**: All outputs now go to ONE timestamped folder per run
- **Files generated**:
  - `characters.json` - Character analysis
  - `gender_swap.json` - Transformed book in JSON
  - `gender_swap.txt` - Print-ready ASCII text

### 4. Added Incremental File Saving
- **Problem**: All data held in memory until end (risky for large books)
- **Solution**: Each file saved immediately when its data is ready
- **Order**: Characters saved → Transformation saved → Text export saved

### 5. Optimized Performance
- **Chunk size**: 32000 tokens for character extraction (better context)
- **Batch size**: 20 paragraphs for transformation (balance of speed/reliability)
- **Result**: ~8-10 minutes for full novel processing

## Current System Architecture

### Core Pipeline Flow
```
1. Parse Book (JSON/Text)
   ↓
2. Extract Characters (with aliases, genders, roles)
   ↓ [saved immediately]
3. Transform Text (using character context)
   ↓ [saved immediately]
4. Export ASCII Text (print-safe)
   ↓ [saved immediately]
5. Complete - All files in one folder
```

### Key Services
- **ParserService** - Handles text/JSON parsing
- **CharacterService** - Extracts and analyzes characters
- **TransformService** - Applies gender transformations
- **TextExportService** - Converts to ASCII for printing
- **QualityService** - Validates output quality (optional)

### Transformation Types Supported
- `gender_swap` - Swaps all genders (male↔female)
- `all_male` - Makes all characters male
- `all_female` - Makes all characters female
- `nonbinary` - Uses they/them pronouns
- `character_analysis` - Just extracts characters
- `parse_only` - Just converts to JSON

## Configuration Settings

**Current optimal settings in `src/config.json`:**
```json
{
  "character": {
    "chunk_size": 32000,  // Large chunks for better context
    "batch_size": 1       // Sequential for OpenAI (avoids rate limits)
  },
  "transform": {
    "chunk_size": 16000,
    "batch_size": 20,     // 20 paragraphs per LLM call
    "llm_temperature": 0.3
  }
}
```

## Commands Reference

### Basic Usage
```bash
# Set up environment
source .env
export DEFAULT_PROVIDER='openai'
export OPENAI_MODEL='gpt-4o-mini'

# Run character analysis only
python regender_cli.py books/json/[book].json character_analysis

# Run full transformation
python regender_cli.py books/json/[book].json gender_swap --no-qc

# With quality control (slower)
python regender_cli.py books/json/[book].json gender_swap
```

### Common Books Available
- `pg1342-Pride_and_Prejudice.json`
- `pg43-The_Strange_Case_of_Dr_Jekyll_and_Mr_Hyde.json`
- `pg76-Adventures_of_Huckleberry_Finn.json`
- `pg1080-A_Modest_Proposal.json`

## Known Issues & Limitations

### Current Issues
1. **Timeout on large batches** - Some paragraphs may fail with 60s timeout
2. **Rate limiting** - OpenAI can throttle on rapid requests
3. **Memory usage** - Large books still use significant RAM during transformation
4. **Character deduplication** - Minor duplicates still occur (e.g., "Tom" vs "Tom Sawyer")

### Performance Expectations
- Short story (<50 pages): 2-5 minutes
- Novella (50-150 pages): 5-10 minutes
- Full novel (200+ pages): 10-20 minutes
- API costs: ~$0.50-2.00 per book with gpt-4o-mini

## Future Improvements to Consider

### High Priority
1. **Streaming output** - Write transformation paragraphs as completed
2. **Resume capability** - Continue from interruption point
3. **Parallel processing** - Process multiple chapters simultaneously
4. **Better progress indication** - Show percentage complete

### Medium Priority
1. **Character importance ranking** - Focus on main characters
2. **Caching** - Cache character analysis for re-runs
3. **Batch mode** - Process multiple books in sequence
4. **Custom pronouns** - Support neo-pronouns and custom sets

### Nice to Have
1. **Web interface** - Upload and process through browser
2. **Format preservation** - Better handling of chapter titles, formatting
3. **Language detection** - Auto-detect non-English text
4. **Selective transformation** - Transform only specific characters

## Testing Checklist

When testing changes, verify:
- [ ] Character extraction finds all characters (including minor ones)
- [ ] Character aliases are properly identified
- [ ] Transformation applies to all character references
- [ ] Output folder contains all 3 files
- [ ] ASCII text is clean (no Unicode)
- [ ] Files are saved incrementally (not all at end)
- [ ] Error handling works (timeouts, API failures)

## Quick Troubleshooting

**Problem**: "Failed to transform batch X-Y"
- **Cause**: API timeout or rate limit
- **Fix**: Reduce batch_size in config.json

**Problem**: Missing characters
- **Cause**: Chunk size too small
- **Fix**: Increase character.chunk_size in config.json

**Problem**: Transformation missing some references
- **Cause**: Character aliases not captured
- **Fix**: Check character.json for missing aliases

**Problem**: Special characters in output text
- **Cause**: Unicode not being converted
- **Fix**: Ensure normalize_method="unidecode" in text export

## Summary of Today's Key Decisions

1. **Let LLMs handle language** - Removed hardcoded gender mappings
2. **Prioritize data safety** - Save files immediately when ready
3. **One folder per run** - All outputs together with timestamp
4. **ASCII for printing** - Clean text output for physical printing
5. **Include all characters** - Even minor ones affect story accuracy

## Next Session Starting Point

The system is now production-ready for basic use. Next priorities should be:
1. Add streaming/progressive output for long books
2. Implement resume capability for interrupted runs
3. Add better progress indicators
4. Consider parallel chapter processing for speed

The codebase is clean, well-organized, and ready for these enhancements.