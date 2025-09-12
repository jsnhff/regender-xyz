# AI-Enhanced Gendered Language Transformation Plan

**Status:** Planning Phase  
**Estimated Implementation:** ~3.5 hours  
**Priority:** High - Significantly improves transformation quality  

## 🎯 **Problem Statement**

The current interactive character selection system successfully handles **basic pronouns** (he/she/him/her) but **misses extensive gendered language** throughout the text.

### **Real Example from A Modest Proposal Transformation:**

**❌ Currently Missed Transformations:**
- `"principal gentleman"` → should be `"principal gentlewoman"`
- `"no gentleman would repine"` → should be `"no gentlewoman would repine"`  
- `"fine gentlemen"` → should be `"fine gentlewomen"`
- `"many gentlemen of this kingdom"` → should be `"many gentlewomen of this kingdom"`
- `"Lord Mayor's feast"` → should be `"Lady Mayor's feast"`
- `"my wife past child-bearing"` → should be `"my husband past child-bearing"`

**Current Coverage:** ~30% of gendered language  
**Target Coverage:** 95%+ of gendered language

## 🤖 **Solution: AI-Assisted Transformation**

### **Why AI Over Comprehensive Dictionary?**

| Approach | Coverage | Accuracy | Maintenance | Context Awareness |
|----------|----------|----------|-------------|-------------------|
| **Dictionary** | ~70% | 95% | High effort | ❌ None |
| **AI-Assisted** | 95%+ | 90% | Low effort | ✅ Full context |
| **Hybrid** | 95%+ | 95% | Medium effort | ✅ Full context |

**AI Advantages:**
- ✅ **Context-aware**: Knows when "gentleman" means gender vs politeness
- ✅ **Comprehensive**: Catches titles, occupations, relationships, idioms  
- ✅ **Scalable**: Works across different eras/styles of literature
- ✅ **Self-updating**: Handles novel/archaic terms automatically
- ✅ **Existing infrastructure**: Already have LLM providers integrated

## 🏗️ **Technical Architecture**

### **Leverage Existing Excellence**

The current `CharacterService` already provides the perfect foundation:

```python
# Current CharacterService patterns we'll reuse:
class CharacterService(BaseService):
    def __init__(self, provider: LLMProvider, strategy, config):
        self.provider = provider              # ✅ Multi-provider support
        self.prompt_generator = PromptGenerator()  # ✅ AI prompting
        self.cache = CharacterCache()         # ✅ Performance optimization
        # ✅ Async processing with concurrency control
```

### **New Service Design**

```python
class GenderedLanguageService(BaseService):
    """AI-powered comprehensive gendered language transformation"""
    
    def __init__(self, provider: LLMProvider, config: ServiceConfig):
        self.provider = provider
        self.prompt_generator = GenderedLanguagePromptGenerator()
        self.cache = TransformationCache()  # Reuse sentence transformations
        super().__init__(config)
    
    async def enhance_transformation_async(self, 
                                          sentence: str, 
                                          character_mappings: dict) -> str:
        """Transform all gendered language in a sentence"""
        
        # Check cache first
        cache_key = f"{hash(sentence)}_{hash(str(character_mappings))}"
        if cached_result := await self.cache.get_async(cache_key):
            return cached_result
        
        # Generate AI prompt
        prompt = self.prompt_generator.generate_transformation_prompt(
            sentence, character_mappings
        )
        
        # Call LLM with same patterns as CharacterService
        response = await self.provider.complete_async(
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ],
            temperature=0.1  # Consistent transformations
        )
        
        # Cache and return
        await self.cache.set_async(cache_key, response)
        return response
```

### **Prompt Engineering**

```python
class GenderedLanguagePromptGenerator:
    def generate_transformation_prompt(self, sentence: str, mappings: dict) -> dict:
        character_context = self._format_character_mappings(mappings)
        
        return {
            "system": """You are a precise literary editor specializing in gender transformation. 
            Transform ALL gendered language in the given sentence while preserving:
            - Original meaning and tone
            - Literary style and voice  
            - Sentence structure
            
            Transform: pronouns, titles, occupations, family relationships, 
            gendered nouns, honorifics, and contextual gender references.
            
            Return ONLY the transformed sentence, no explanations.""",
            
            "user": f"""Transform this sentence according to character changes:
            
            Character Transformations:
            {character_context}
            
            Original Sentence: "{sentence}"
            
            Transformed Sentence:"""
        }
    
    def _format_character_mappings(self, mappings: dict) -> str:
        context_lines = []
        for char_name, mapping in mappings.items():
            if mapping['original_gender'] != mapping['new_gender']:
                context_lines.append(
                    f"• {mapping['original_name']} ({mapping['original_gender'].value}) "
                    f"→ {mapping['new_name']} ({mapping['new_gender'].value})"
                )
        return "\n".join(context_lines)
```

## 🔧 **Implementation Plan**

### **Phase 1: Core Service (2 hours)**
1. **Create `GenderedLanguageService`** following `CharacterService` patterns
2. **Implement prompt generation** with character-aware context
3. **Add caching layer** for sentence-level transformations
4. **Unit tests** for core functionality

### **Phase 2: CLI Integration (30 minutes)**  
1. **Add `--ai-enhance` flag** to `regender_cli.py`
2. **Hook into existing transformation pipeline** in `apply_custom_transformation()`
3. **Graceful fallback** to current dictionary-only mode if AI unavailable

### **Phase 3: Performance Optimization (30 minutes)**
1. **Batch processing** multiple sentences per API call
2. **Smart caching** to avoid reprocessing identical sentences  
3. **Rate limiting** using existing provider concurrency controls
4. **Progress indicators** for longer transformations

### **Phase 4: Testing & Polish (30 minutes)**
1. **Test with A Modest Proposal** to verify comprehensive transformation
2. **Test with different character combinations** 
3. **Performance benchmarking** against dictionary-only approach
4. **Error handling** and fallback validation

## 📊 **Cost/Benefit Analysis**

### **Development Investment**
- **Time**: ~3.5 hours total implementation
- **Complexity**: Low (reuses existing patterns)
- **Risk**: Low (graceful fallbacks, optional feature)

### **Operating Costs**
- **API costs**: ~$0.10-0.30 per book (estimated)
- **Processing time**: +2-5 seconds per book
- **Caching benefits**: 80%+ cost reduction on repeated content

### **Quality Improvement**
- **Current**: 30% gendered language coverage  
- **Target**: 95%+ gendered language coverage
- **Accuracy**: Dictionary (95%) + AI context-awareness
- **User satisfaction**: Comprehensive transformations vs partial

## 🎛️ **User Experience**

### **CLI Usage**
```bash
# Current (dictionary-only)
python regender_cli.py book.json --interactive

# Enhanced (AI-powered comprehensive)  
python regender_cli.py book.json --interactive --ai-enhance

# Fallback behavior if AI unavailable
python regender_cli.py book.json --interactive --ai-enhance
# → Automatically falls back to dictionary-only with warning
```

### **User Control**
- **Optional feature**: `--ai-enhance` flag (defaults to current behavior)
- **Transparent fallback**: Works even if AI providers fail
- **Progress feedback**: Shows AI enhancement status
- **Cost awareness**: Optional cost estimation display

## 🔄 **Integration Points**

### **Existing Code Modifications**

**File: `regender_cli.py`**
```python
# Add CLI argument
parser.add_argument('--ai-enhance', action='store_true', 
                   help='Use AI for comprehensive gendered language transformation')

# Modify apply_custom_transformation()
if args.ai_enhance and app.get_service('gendered_language'):
    enhanced_text = await gendered_language_service.enhance_transformation_async(
        transformed_text, custom_mappings
    )
```

**File: `src/config.json`**
```json
{
  "services": {
    "gendered_language": {
      "class": "src.services.gendered_language_service.GenderedLanguageService",
      "config": {"cache_enabled": true, "max_concurrent": 3},
      "dependencies": {"provider": "llm_provider"}
    }
  }
}
```

## ✅ **Success Metrics**

### **Quality Metrics**
- [ ] **A Modest Proposal test**: All gentleman/gentlewoman transformations correct
- [ ] **Complex relationship terms**: wife/husband, lord/lady, etc. transformed  
- [ ] **Context preservation**: Literary style and meaning maintained
- [ ] **Edge case handling**: Archaic terms, compound words, idioms

### **Performance Metrics**  
- [ ] **Processing time**: <10 seconds additional per book
- [ ] **Cache hit rate**: >80% on repeated content
- [ ] **Cost efficiency**: <$0.50 per book including caching benefits
- [ ] **Graceful degradation**: 100% fallback success rate

### **User Experience Metrics**
- [ ] **Backwards compatibility**: All existing functionality preserved
- [ ] **Clear feedback**: Users understand when AI enhancement active
- [ ] **Error handling**: Helpful messages if AI unavailable
- [ ] **Documentation**: Usage examples and cost guidance

## 🚀 **Next Steps**

1. **Review and approve** this technical plan
2. **Set up development environment** with API keys
3. **Begin Phase 1 implementation** using existing `CharacterService` patterns  
4. **Test with A Modest Proposal** for immediate validation
5. **Iterate on prompt engineering** for optimal results

## 📝 **Notes for Implementation**

- **Reuse existing architecture** - Don't reinvent the wheel
- **Follow established patterns** - Same style as `CharacterService`
- **Maintain backwards compatibility** - All current functionality preserved
- **Add comprehensive testing** - Especially for edge cases and fallbacks
- **Document thoroughly** - Usage examples, cost implications, fallback behavior

---

**This plan leverages the excellent foundation already built while extending it to handle comprehensive gendered language transformation through AI assistance.**