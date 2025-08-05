"""Rate-limited character analyzer that respects API token limits."""

import json
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from api_client import UnifiedLLMClient
from .smart_chunked_analyzer import extract_chapters_text, analyze_chunk_with_context, merge_characters_smart


class RateLimitedAnalyzer:
    """Analyzer that tracks token usage and respects rate limits."""
    
    def __init__(self, tokens_per_minute: int = 16000, model: str = "grok-4-latest", provider: str = "grok"):
        self.tokens_per_minute = tokens_per_minute
        self.model = model
        self.provider = provider
        self.client = UnifiedLLMClient(provider=provider)
        
        # Token tracking
        self.tokens_used = 0
        self.window_start = datetime.now()
        self.chunk_history = []
        
        # Safety margin (80% of limit)
        self.safe_limit = int(self.tokens_per_minute * 0.8)
        
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 1 token per 4 characters)."""
        return len(text) // 4
    
    def can_process_chunk(self, estimated_tokens: int) -> bool:
        """Check if we can process a chunk without exceeding rate limit."""
        # Reset window if minute has passed
        if datetime.now() - self.window_start > timedelta(minutes=1):
            self.tokens_used = 0
            self.window_start = datetime.now()
            
        return (self.tokens_used + estimated_tokens) <= self.safe_limit
    
    def wait_for_rate_limit(self, verbose: bool = True):
        """Wait until rate limit window resets."""
        time_passed = (datetime.now() - self.window_start).total_seconds()
        wait_time = max(0, 61 - time_passed)  # 61 seconds to be safe
        
        if wait_time > 0 and verbose:
            print(f"\n⏳ Rate limit approaching. Waiting {int(wait_time)} seconds...")
            for i in range(int(wait_time), 0, -1):
                print(f"\r   {i} seconds remaining...", end='', flush=True)
                time.sleep(1)
            print("\r   Ready to continue!        ")
            
        # Reset counter
        self.tokens_used = 0
        self.window_start = datetime.now()
    
    def analyze_book_with_rate_limits(
        self,
        book_data: Dict[str, Any],
        max_chunks: Optional[int] = None,
        verbose: bool = True
    ) -> Tuple[Dict[str, Any], str]:
        """
        Analyze a book respecting rate limits.
        
        Strategy:
        1. Create optimal chunks based on book size
        2. Process chunks until rate limit approached
        3. Wait if needed and continue
        4. Return complete character analysis
        """
        if verbose:
            print("📖 Analyzing book with rate limit awareness...")
            
        chapters = book_data.get('chapters', [])
        total_chapters = len(chapters)
        
        if total_chapters == 0:
            return {}, "No chapters found"
            
        # Create smart chunks
        chunks = self._create_smart_chunks(chapters, verbose)
        
        if max_chunks:
            chunks = chunks[:max_chunks]
            
        all_characters = {}
        chunks_processed = 0
        
        for i, chunk in enumerate(chunks):
            # Extract text
            chunk_text = extract_chapters_text(chapters, chunk['chapters'])
            
            # Estimate tokens (prompt + content)
            prompt_overhead = 1000  # Rough estimate for prompt
            estimated_tokens = self.estimate_tokens(chunk_text) + prompt_overhead
            
            # Check rate limit
            if not self.can_process_chunk(estimated_tokens):
                self.wait_for_rate_limit(verbose)
                
            if verbose:
                print(f"\n🔍 Processing chunk {i+1}/{len(chunks)}: {chunk['name']}")
                print(f"   Estimated tokens: {estimated_tokens:,}")
                print(f"   Rate limit usage: {self.tokens_used:,}/{self.safe_limit:,}")
                
            # Process chunk
            chunk_context = f"[Analyzing {chunk['name']} - Chapters {chunk['chapters'][0]+1} to {chunk['chapters'][-1]+1} of {total_chapters}]"
            
            try:
                chunk_chars = analyze_chunk_with_context(
                    chunk_text,
                    self.model,
                    self.client,
                    chunk_context,
                    chunk_num=i+1,
                    total_chunks=len(chunks),
                    verbose=verbose
                )
                
                # Update token usage
                self.tokens_used += estimated_tokens
                
                # Track chunk
                self.chunk_history.append({
                    'chunk': chunk['name'],
                    'tokens': estimated_tokens,
                    'characters_found': len(chunk_chars),
                    'timestamp': datetime.now().isoformat()
                })
                
                # Merge results
                all_characters = merge_characters_smart(all_characters, chunk_chars, chunk['name'])
                chunks_processed += 1
                
                if verbose:
                    print(f"   Found {len(chunk_chars)} characters")
                    print(f"   Total unique characters: {len(all_characters)}")
                    
            except Exception as e:
                if verbose:
                    print(f"   ⚠️  Error processing chunk: {e}")
                    
        # Create context
        from .context import create_character_context
        context = create_character_context(all_characters)
        
        if verbose:
            print(f"\n✅ Analysis complete!")
            print(f"   Chunks processed: {chunks_processed}/{len(chunks)}")
            print(f"   Total characters found: {len(all_characters)}")
            print(f"   Total tokens used: {sum(c['tokens'] for c in self.chunk_history):,}")
            
        return all_characters, context
    
    def _create_smart_chunks(self, chapters: List[Dict], verbose: bool = True) -> List[Dict]:
        """Create intelligent chunks that maximize coverage within token limits."""
        total_chapters = len(chapters)
        chunks = []
        
        # Estimate total book size
        total_text = extract_chapters_text(chapters, list(range(total_chapters)))
        total_tokens = self.estimate_tokens(total_text)
        
        if verbose:
            print(f"   Book size: {total_chapters} chapters, ~{total_tokens:,} tokens")
            
        # For small books, analyze all at once
        if total_tokens < 10000:
            chunks.append({
                'name': 'Complete Book',
                'chapters': list(range(total_chapters)),
                'priority': 1
            })
            return chunks
            
        # For larger books, create strategic chunks
        # Each chunk should be ~10k tokens to stay under limit with prompt
        target_chunk_size = 10000
        
        # Priority 1: Beginning (character introductions)
        begin_chapters = []
        begin_tokens = 0
        for i in range(min(total_chapters // 3, total_chapters)):
            chapter_text = extract_chapters_text(chapters, [i])
            chapter_tokens = self.estimate_tokens(chapter_text)
            if begin_tokens + chapter_tokens > target_chunk_size:
                break
            begin_chapters.append(i)
            begin_tokens += chapter_tokens
            
        if begin_chapters:
            chunks.append({
                'name': f'Beginning (Ch 1-{len(begin_chapters)})',
                'chapters': begin_chapters,
                'priority': 1
            })
            
        # Priority 2: Key middle sections
        middle_start = total_chapters // 3
        middle_end = 2 * total_chapters // 3
        
        middle_chunks = self._split_into_chunks(
            chapters, 
            list(range(middle_start, middle_end)),
            target_chunk_size,
            'Middle'
        )
        chunks.extend(middle_chunks)
        
        # Priority 3: End sections
        end_chunks = self._split_into_chunks(
            chapters,
            list(range(middle_end, total_chapters)),
            target_chunk_size,
            'End'
        )
        chunks.extend(end_chunks)
        
        # Priority 4: Sample any remaining sections
        if len(chunks) * target_chunk_size < total_tokens * 0.5:
            # We're missing significant portions, add samples
            sampled_chapters = list(range(0, total_chapters, max(1, total_chapters // 10)))
            sample_chunk = {
                'name': 'Sampled Sections',
                'chapters': sampled_chapters[:20],  # Limit sample size
                'priority': 4
            }
            chunks.append(sample_chunk)
            
        return chunks
    
    def _split_into_chunks(
        self, 
        chapters: List[Dict], 
        chapter_indices: List[int], 
        target_size: int,
        section_name: str
    ) -> List[Dict]:
        """Split a section into token-sized chunks."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_num = 1
        
        for idx in chapter_indices:
            chapter_text = extract_chapters_text(chapters, [idx])
            chapter_tokens = self.estimate_tokens(chapter_text)
            
            if current_tokens + chapter_tokens > target_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'name': f'{section_name} Part {chunk_num}',
                    'chapters': current_chunk,
                    'priority': 2 if section_name == 'Middle' else 3
                })
                chunk_num += 1
                current_chunk = [idx]
                current_tokens = chapter_tokens
            else:
                current_chunk.append(idx)
                current_tokens += chapter_tokens
                
        # Add remaining
        if current_chunk:
            chunks.append({
                'name': f'{section_name} Part {chunk_num}',
                'chapters': current_chunk,
                'priority': 2 if section_name == 'Middle' else 3
            })
            
        return chunks


def analyze_book_with_rate_limits(
    book_file: str,
    output_file: str,
    model: str = "grok-4-latest",
    provider: str = "grok",
    tokens_per_minute: int = 16000,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to analyze a book with rate limit handling.
    """
    # Load book
    with open(book_file, 'r') as f:
        book_data = json.load(f)
        
    # Create analyzer
    analyzer = RateLimitedAnalyzer(
        tokens_per_minute=tokens_per_minute,
        model=model,
        provider=provider
    )
    
    # Analyze
    characters, context = analyzer.analyze_book_with_rate_limits(
        book_data,
        verbose=verbose
    )
    
    # Save results
    output_data = {
        "metadata": {
            "source_book": book_file,
            "analysis_model": model,
            "analysis_provider": provider,
            "character_count": len(characters),
            "analysis_method": "rate_limited_progressive",
            "token_limit": tokens_per_minute,
            "chunks_processed": len(analyzer.chunk_history)
        },
        "characters": characters,
        "context": context,
        "analysis_history": analyzer.chunk_history
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
        
    if verbose:
        print(f"\n✅ Saved {len(characters)} characters to: {output_file}")
        
    return characters