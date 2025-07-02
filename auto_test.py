#!/usr/bin/env python3
"""
AUTO TEST MODE - Rapid Gender Transformation Testing
Automatically tests different approaches and logs results for analysis.
"""

import time
import json
from datetime import datetime
from pathlib import Path
from ai_chunking import chunk_text_ai
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters
from validate_transformation import quick_validation_report
import re

class AutoTester:
    def __init__(self, log_file="auto_test_log.json"):
        self.log_file = log_file
        self.test_results = []
        
    def log_test(self, test_config, results):
        """Log test configuration and results."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "config": test_config,
            "results": results
        }
        self.test_results.append(entry)
        
        # Save to file
        with open(self.log_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
    
    def quick_pronoun_check(self, text):
        """Quick check for pronoun transformation success."""
        gendered_pronouns = len(re.findall(r'\b(he|she|him|her|his)\b', text, re.IGNORECASE))
        neutral_pronouns = len(re.findall(r'\b(they|them|their)\b', text, re.IGNORECASE))
        return {
            "gendered_count": gendered_pronouns,
            "neutral_count": neutral_pronouns,
            "ratio": neutral_pronouns / max(1, gendered_pronouns + neutral_pronouns)
        }
    
    def test_transformation_approach(self, chunks, character_context, test_config):
        """Test a specific transformation approach."""
        print(f"\n🧪 Testing: {test_config['name']}")
        print(f"   Model: {test_config['model']}")
        print(f"   Approach: {test_config['description']}")
        
        # Test on first 5 chunks
        test_chunks = chunks[:5]
        results = {
            "chunks_tested": 5,
            "total_chars": sum(chunk['size'] for chunk in test_chunks),
            "transformations": [],
            "errors": 0,
            "total_time": 0
        }
        
        start_time = time.time()
        
        for i, chunk in enumerate(test_chunks):
            chunk_start = time.time()
            
            try:
                # Use the specific transformation approach
                if test_config['approach'] == 'standard':
                    transformed_text, changes = transform_gender_with_context(
                        chunk['text'],
                        test_config['transform_type'],
                        character_context,
                        model=test_config['model']
                    )
                elif test_config['approach'] == 'focused_prompt':
                    # Try a more focused prompt
                    focused_context = f"""CRITICAL: Transform ALL gendered pronouns to neutral.
                    
{character_context}

RULES - APPLY TO EVERY INSTANCE:
- he/He → they/They
- she/She → they/They  
- him/Him → them/Them
- her/Her → them/Them (when object)
- his/His → their/Their
- Mr./Mrs./Ms./Miss → Mx.

Be consistent and systematic."""
                    
                    transformed_text, changes = transform_gender_with_context(
                        chunk['text'],
                        test_config['transform_type'],
                        focused_context,
                        model=test_config['model']
                    )
                elif test_config['approach'] == 'simple_prompt':
                    # Very simple instruction
                    simple_context = "Transform all he/she to they, him/her to them, his/her to their. Transform Mr./Mrs./Ms. to Mx."
                    
                    transformed_text, changes = transform_gender_with_context(
                        chunk['text'],
                        test_config['transform_type'],
                        simple_context,
                        model=test_config['model']
                    )
                
                chunk_time = time.time() - chunk_start
                
                # Quick analysis
                pronoun_check = self.quick_pronoun_check(transformed_text)
                
                chunk_result = {
                    "chunk_index": i,
                    "chunk_description": chunk['description'],
                    "original_size": chunk['size'],
                    "transformed_size": len(transformed_text),
                    "changes_count": len(changes),
                    "processing_time": chunk_time,
                    "pronoun_analysis": pronoun_check,
                    "sample_changes": changes[:3] if changes else []
                }
                
                results["transformations"].append(chunk_result)
                
                print(f"   Chunk {i+1}: {len(changes)} changes, {pronoun_check['neutral_count']} neutral pronouns")
                
            except Exception as e:
                results["errors"] += 1
                print(f"   ❌ Chunk {i+1} failed: {e}")
        
        results["total_time"] = time.time() - start_time
        
        # Calculate overall metrics
        total_neutral = sum(t["pronoun_analysis"]["neutral_count"] for t in results["transformations"])
        total_gendered = sum(t["pronoun_analysis"]["gendered_count"] for t in results["transformations"])
        total_changes = sum(t["changes_count"] for t in results["transformations"])
        
        results["summary"] = {
            "avg_time_per_chunk": results["total_time"] / 5,
            "total_changes": total_changes,
            "total_neutral_pronouns": total_neutral,
            "total_gendered_remaining": total_gendered,
            "success_rate": total_neutral / max(1, total_neutral + total_gendered),
            "error_rate": results["errors"] / 5
        }
        
        print(f"   📊 Results: {total_changes} changes, {total_neutral} neutral pronouns added")
        print(f"   🎯 Success rate: {results['summary']['success_rate']:.1%}")
        
        return results
    
    def run_auto_tests(self, book_path="test_data/pride_and_prejudice_full.txt"):
        """Run a series of automated tests with different approaches."""
        
        print("🚀 AUTO TEST MODE - Rapid Gender Transformation Testing")
        print("=" * 80)
        
        # Load book and setup
        with open(book_path, 'r') as f:
            text = f.read()
        
        print(f"📚 Testing on: {book_path}")
        print(f"📊 Book size: {len(text):,} characters")
        
        # Get chunks
        print("\n🔧 Creating chunks...")
        chunks = chunk_text_ai(text, prefer_ai=False)
        print(f"✅ {len(chunks)} chunks created")
        
        # Basic character analysis
        print("\n👥 Quick character analysis...")
        try:
            sample_text = ''.join(chunks[i]['text'] for i in range(min(3, len(chunks))))[:50000]
            character_analysis = analyze_characters(sample_text)
            characters_dict = character_analysis.get('characters', {})
            character_context = "Character information:\n"
            for name, info in list(characters_dict.items())[:5]:
                character_context += f"- {name}: {info.get('gender', 'unknown')}\n"
        except:
            character_context = "Main characters from Pride and Prejudice"
        
        # Define test configurations
        test_configs = [
            {
                "name": "Standard GPT-4.1-nano",
                "model": "gpt-4.1-nano",
                "approach": "standard",
                "transform_type": "neutral",
                "description": "Current default approach"
            },
            {
                "name": "Focused Prompt GPT-4.1-nano", 
                "model": "gpt-4.1-nano",
                "approach": "focused_prompt",
                "transform_type": "neutral",
                "description": "More explicit instructions"
            },
            {
                "name": "Simple Prompt GPT-4.1-nano",
                "model": "gpt-4.1-nano", 
                "approach": "simple_prompt",
                "transform_type": "neutral",
                "description": "Very simple transformation rules"
            },
            {
                "name": "Standard GPT-4o-mini",
                "model": "gpt-4o-mini",
                "approach": "standard", 
                "transform_type": "neutral",
                "description": "Different model, same approach"
            },
            {
                "name": "Focused Prompt GPT-4o-mini",
                "model": "gpt-4o-mini",
                "approach": "focused_prompt",
                "transform_type": "neutral", 
                "description": "Better model + explicit instructions"
            }
        ]
        
        # Run tests
        print(f"\n🧪 Running {len(test_configs)} test configurations...")
        
        for i, config in enumerate(test_configs, 1):
            print(f"\n{'='*60}")
            print(f"TEST {i}/{len(test_configs)}")
            
            try:
                results = self.test_transformation_approach(chunks, character_context, config)
                self.log_test(config, results)
                
                # Show summary
                summary = results["summary"]
                print(f"   ⏱️ Time: {summary['avg_time_per_chunk']:.1f}s per chunk")
                print(f"   🔄 Changes: {summary['total_changes']}")
                print(f"   ✅ Success: {summary['success_rate']:.1%}")
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
                error_result = {"error": str(e), "timestamp": datetime.now().isoformat()}
                self.log_test(config, error_result)
        
        # Analyze results and recommend best approach
        self.analyze_and_recommend()
    
    def analyze_and_recommend(self):
        """Analyze test results and recommend the best approach."""
        print(f"\n" + "="*80)
        print("📊 TEST ANALYSIS & RECOMMENDATIONS")
        print("="*80)
        
        if not self.test_results:
            print("❌ No test results to analyze")
            return
        
        # Find best performing configurations
        valid_results = [r for r in self.test_results if "error" not in r["results"]]
        
        if not valid_results:
            print("❌ All tests failed - check model availability and API keys")
            return
        
        # Sort by success rate
        sorted_results = sorted(valid_results, 
                              key=lambda x: x["results"]["summary"]["success_rate"], 
                              reverse=True)
        
        print("🏆 RANKING BY SUCCESS RATE:")
        for i, result in enumerate(sorted_results, 1):
            config = result["config"]
            summary = result["results"]["summary"]
            
            print(f"{i}. {config['name']}")
            print(f"   Success Rate: {summary['success_rate']:.1%}")
            print(f"   Avg Time: {summary['avg_time_per_chunk']:.1f}s")
            print(f"   Total Changes: {summary['total_changes']}")
            print(f"   Model: {config['model']}, Approach: {config['approach']}")
            print()
        
        # Recommendations
        best = sorted_results[0]
        best_config = best["config"]
        best_summary = best["results"]["summary"]
        
        print("💡 RECOMMENDATIONS:")
        
        if best_summary["success_rate"] >= 0.8:
            print(f"✅ EXCELLENT: Use '{best_config['name']}' approach")
            print(f"   This achieved {best_summary['success_rate']:.1%} success rate")
        elif best_summary["success_rate"] >= 0.6:
            print(f"👍 GOOD: '{best_config['name']}' is working reasonably well")
            print(f"   Consider fine-tuning the prompt for better results")
        else:
            print(f"⚠️ ISSUES DETECTED: Best approach only achieved {best_summary['success_rate']:.1%}")
            print("   Problems likely include:")
            print("   - Model not following instructions consistently")
            print("   - Context window too large")
            print("   - Need more specific prompts")
        
        # Save best config for easy reuse
        with open("best_config.json", "w") as f:
            json.dump(best_config, f, indent=2)
        
        print(f"\n💾 Best configuration saved to: best_config.json")
        print(f"📝 Full test log saved to: {self.log_file}")

def main():
    """Run auto tests."""
    tester = AutoTester()
    tester.run_auto_tests()

if __name__ == "__main__":
    main()