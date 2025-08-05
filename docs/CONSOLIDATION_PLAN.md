# Consolidation Plan for Regender-XYZ

## Executive Summary

This plan outlines the consolidation of Regender-XYZ into a unified, high-quality analysis and output tool. The goal is to merge the best features from different workflows while eliminating redundancy and improving overall system quality.

## Current State Analysis

### Strengths
1. **Multiple workflows** provide flexibility
2. **Character analysis** improves transformation accuracy
3. **Quality control loop** catches missed transformations
4. **Rate limiting** handles API constraints
5. **Multi-provider support** offers redundancy

### Weaknesses
1. **Fragmented pipelines** - separate tools for transform and QC
2. **Inconsistent interfaces** - different commands for related tasks
3. **Manual coordination** - user must run multiple steps
4. **Duplicate functionality** - similar code in different modules
5. **Limited integration** - workflows don't share context

## Consolidation Goals

1. **Unified Pipeline**: Single command for complete transformation with QC
2. **Automatic Optimization**: Smart selection of models and chunking
3. **Integrated Character Analysis**: Built into transformation by default
4. **Progressive Enhancement**: Quality improves with each stage
5. **Seamless Rate Limiting**: Automatic handling across all operations

## Phase 1: Core Unification (Week 1-2)

### 1.1 Unified Transform Command
Create a single transform command that includes:
- Character analysis (automatic if not provided)
- Transformation with best available model
- Quality control loop (automatic)
- Progress tracking and resumability

```bash
# New unified command
python regender_book_cli.py transform books/json/pg1342.json \
    --type all_male \
    --quality high  # Triggers full pipeline
```

### 1.2 Pipeline Configuration
```python
# config/pipelines.json
{
  "quality_levels": {
    "fast": {
      "character_analysis": false,
      "quality_control": false,
      "model_tier": "standard"
    },
    "standard": {
      "character_analysis": true,
      "quality_control": false,
      "model_tier": "advanced"
    },
    "high": {
      "character_analysis": true,
      "quality_control": true,
      "model_tier": "flagship",
      "qc_iterations": 3
    }
  }
}
```

### 1.3 Consolidate Modules
Merge related functionality:
- `book_transform/` + `review_loop.py` → `book_transform/pipeline.py`
- `book_characters/analyzer.py` + `rate_limited_analyzer.py` → `book_characters/unified_analyzer.py`
- Create `book_transform/quality_control.py` from review_loop

## Phase 2: Smart Features (Week 3-4)

### 2.1 Automatic Model Selection
```python
class ModelSelector:
    def select_best_model(self, book_size, transform_type, quality_level):
        # Logic to choose optimal model based on:
        # - Book size vs context window
        # - Transform complexity
        # - Available API quota
        # - Quality requirements
```

### 2.2 Intelligent Chunking
```python
class SmartChunker:
    def create_chunks(self, book_data, model_config, preserve_context=True):
        # Adaptive chunking based on:
        # - Chapter boundaries
        # - Character appearances
        # - Narrative sections
        # - Model context window
```

### 2.3 Cached Character Analysis
- Store character analysis with content hash
- Reuse for multiple transformations
- Update incrementally if book changes

## Phase 3: Quality Assurance (Week 5-6)

### 3.1 Transformation Scoring
```python
class QualityScorer:
    def score_transformation(self, original, transformed, transform_type):
        return {
            "completeness": 0.95,  # % of expected changes made
            "accuracy": 0.98,      # % of correct transformations
            "consistency": 0.97,   # Character gender consistency
            "readability": 0.99    # Grammar and flow preserved
        }
```

### 3.2 Automatic Validation
- Built-in checks for common errors
- Pattern-based validation
- LLM-based semantic validation
- Automatic correction attempts

### 3.3 Quality Reports
Generate detailed reports:
```
Transformation Quality Report
============================
Book: Pride and Prejudice
Transform: all_male
Overall Score: 96.7%

Details:
- Characters transformed: 23/23 (100%)
- Pronouns updated: 1,847/1,852 (99.7%)
- Dialogue attribution: 412/413 (99.8%)
- Possessives handled: 687/692 (99.3%)

Issues Found:
- 5 ambiguous pronouns requiring context
- 2 nested quotes needing manual review
```

## Phase 4: Advanced Features (Week 7-8)

### 4.1 Parallel Processing
- Process multiple chapters simultaneously
- Coordinate rate limits across parallel requests
- Merge results intelligently

### 4.2 Progressive Transformation
```python
class ProgressiveTransformer:
    def transform(self, book_data, transform_type):
        # Stage 1: Character analysis
        characters = self.analyze_characters_with_cache()
        
        # Stage 2: Context mapping
        context_map = self.build_context_map(characters)
        
        # Stage 3: Chunked transformation
        chunks = self.transform_chunks_parallel(context_map)
        
        # Stage 4: Quality control
        refined = self.quality_control_loop(chunks)
        
        # Stage 5: Final validation
        return self.validate_and_score(refined)
```

### 4.3 API Optimization
- Automatic failover between providers
- Cost optimization (use cheaper models when possible)
- Quota management across team members
- Request batching and caching

## Implementation Timeline

### Week 1-2: Core Unification
- [ ] Design unified pipeline architecture
- [ ] Merge transformation and QC modules
- [ ] Create pipeline configuration system
- [ ] Implement basic unified command

### Week 3-4: Smart Features
- [ ] Build model selection logic
- [ ] Implement intelligent chunking
- [ ] Add character analysis caching
- [ ] Create progress tracking

### Week 5-6: Quality Assurance
- [ ] Develop scoring system
- [ ] Build validation framework
- [ ] Create quality reports
- [ ] Add automatic corrections

### Week 7-8: Advanced Features
- [ ] Implement parallel processing
- [ ] Build progressive transformation
- [ ] Add API optimization
- [ ] Complete integration testing

## Success Metrics

1. **Simplicity**: Reduce 5+ commands to 1-2 for common workflows
2. **Quality**: 95%+ transformation accuracy on test corpus
3. **Performance**: 2x faster for typical books through parallelization
4. **Reliability**: 99%+ success rate with automatic retry/failover
5. **Cost**: 30% reduction through smart model selection

## Migration Strategy

1. **Backward Compatibility**: Keep existing commands working
2. **Gradual Rollout**: New features available via flags
3. **Documentation**: Update all docs with new workflows
4. **Testing**: Comprehensive test suite for new pipeline
5. **Monitoring**: Track quality metrics in production

## Risk Mitigation

1. **API Changes**: Abstract provider interfaces further
2. **Rate Limits**: Implement robust queuing and retry
3. **Quality Regression**: A/B test new vs old pipeline
4. **Complexity**: Keep simple mode for basic users
5. **Breaking Changes**: Version lock for stability

## Next Steps

1. Review and approve this plan
2. Set up development branch for consolidation
3. Begin Phase 1 implementation
4. Weekly progress reviews
5. User testing at each phase completion

## Appendix: Technical Details

### A. Unified Pipeline Architecture
```
Input → Validator → Character Analyzer → Context Builder →
Chunker → Transformer → Quality Controller → Validator → Output
         ↓                    ↓                   ↓
      [Cache]            [Rate Limiter]      [Error Handler]
```

### B. Configuration Schema
```json
{
  "pipeline": {
    "version": "2.0",
    "stages": ["validate", "analyze", "transform", "qc", "report"],
    "quality_presets": {...},
    "model_selection": {...},
    "rate_limits": {...}
  }
}
```

### C. API Interface
```python
# New unified API
result = RegenderPipeline().transform(
    input_file="book.json",
    transform_type="all_male",
    quality="high",
    options={
        "parallel": True,
        "cache": True,
        "report": True
    }
)
```