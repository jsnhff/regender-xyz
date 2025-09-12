# Continuation Prompt for Repository Cleanup

## Context
We're working on cleaning and modernizing the regender-xyz repository, a command-line tool for analyzing and transforming gender representation in literature using LLM providers (OpenAI, Anthropic).

## Work Completed So Far

### 1. Root Directory Cleanup ✅
- Removed 7 temporary output files (~1.6MB)
- Deleted Python cache directories (__pycache__)
- Moved test scripts to tests/
- Archived 4 old/duplicate scripts to archive/old_scripts/
- Updated .gitignore to prevent future cruft

### 2. Ruff Integration ✅
- Created pyproject.toml with Ruff configuration
- Set up .claude/hooks.json for automatic linting
- Fixed 1,038+ formatting issues
- Updated requirements.txt with ruff dependency

### 3. src/ Folder Improvements ✅
- Cleaned all Python cache files
- Consolidated provider system (archived unused openai_provider.py, anthropic_provider.py)
- Modernized 255 type hints (Dict → dict, List → list)
- Fixed container.py type errors and variable shadowing
- Verified all functionality works with API keys

## Current Repository State

### Structure
```
regender-xyz/
├── src/              # Core application (clean, modernized)
├── books/            # 90+ Project Gutenberg texts
├── tests/            # Test suite
├── docs/             # Documentation
├── archive/          # Old/unused code
├── download/         # Gutenberg downloader
└── regender_cli.py   # Main CLI entry point
```

### Key Stats
- ~7,800 lines of Python code in src/
- Service-oriented architecture with 4 main services
- 16 strategy implementations
- 7 specialized parsers
- Supports OpenAI and Anthropic providers (Grok removed)

### Environment
- Python 3.9+ with modern type hints
- Ruff configured for linting/formatting
- .env configured with OpenAI API key
- All tests passing, CLI functional

## Next Steps to Continue

### Priority 1: Testing & Quality
1. **Run full test suite** - Check what's passing/failing in tests/
2. **Add missing tests** - Ensure critical paths have coverage
3. **Fix any broken tests** - Update tests for removed Grok provider
4. **Add pytest configuration** - Create pytest.ini for better test running

### Priority 2: Documentation
1. **Update README.md** - Ensure it reflects current state (no Grok)
2. **API documentation** - Generate from docstrings
3. **Usage examples** - Add more practical examples
4. **CHANGELOG.md** - Document recent changes

### Priority 3: Code Quality
1. **Check for dead code** - Find and remove unused functions/classes
2. **Improve error handling** - Add more specific exception types
3. **Add logging configuration** - Set up proper log rotation
4. **Review TODO/FIXME comments** - Address or remove them

### Priority 4: Performance & Features
1. **Profile performance** - Identify bottlenecks
2. **Add progress bars** - For long-running operations
3. **Implement caching** - Reduce redundant API calls
4. **Add batch processing** - Process multiple books efficiently

### Priority 5: Deployment & Distribution
1. **Create setup.py** - For pip installation
2. **Add Docker support** - Create Dockerfile
3. **GitHub Actions** - Set up CI/CD pipeline
4. **Create release** - Tag and release current version

## Key Areas Needing Attention

### Immediate Issues
- **books/ folder** - Very large (90+ books), consider .gitignore or separate repo
- **Missing tests** - Some services lack test coverage
- **Error messages** - Some are too verbose (provider initialization)
- **Hardcoded paths** - Some paths assume specific directory structure

### Technical Debt
- **Provider redundancy** - legacy_client.py could be refactored
- **Large parser files** - Could benefit from further modularization
- **Async consistency** - Mix of sync/async patterns
- **Type completeness** - Some functions still missing return type hints

## Questions to Address
1. Should the books/ folder be in the repo or downloaded on demand?
2. Is the archive/ folder needed or should it be removed?
3. Should we add support for local LLMs (Ollama, llama.cpp)?
4. Do we need a web interface or API server mode?
5. Should character data be saved separately for reuse?

## Commands to Run Next
```bash
# Check test status
python -m pytest tests/ -v

# Find dead code
vulture src/ --min-confidence 80

# Check code complexity
radon cc src/ -s

# Generate coverage report
pytest --cov=src tests/

# Find security issues
bandit -r src/
```

## Important Files to Review
1. `src/providers/legacy_client.py` - Main provider logic (482 lines)
2. `src/parsers/gutenberg.py` - Largest parser (577 lines)
3. `src/services/transform_service.py` - Core transformation logic
4. `tests/` - Verify test coverage
5. `.env.example` - Ensure it's up to date

## Success Metrics
- [ ] All tests passing
- [ ] 80%+ code coverage
- [ ] No security vulnerabilities
- [ ] Documentation complete
- [ ] Can be installed via pip
- [ ] Docker image builds successfully
- [ ] CI/CD pipeline working

## Notes for Next Session
- API key is configured and working (OpenAI)
- Ruff is set up as a Claude hook
- All Python files are formatted and type hints modernized
- The application core is functional and tested
- Focus should be on testing, documentation, and distribution

Remember: The goal is to make this a professional, maintainable, and easy-to-use tool for literary gender analysis and transformation.