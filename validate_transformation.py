#!/usr/bin/env python3
"""
TRANSFORMATION VALIDATION SYSTEM
Fast quality assurance for gender transformation accuracy.
"""

import re
import random
from pathlib import Path
from collections import Counter

def analyze_gendered_language(text):
    """Analyze gendered language patterns in text."""
    
    # Define patterns to check
    patterns = {
        'pronouns_he_she': r'\b(he|she|He|She)\b',
        'pronouns_him_her': r'\b(him|her|Him|Her)\b', 
        'pronouns_his_her': r'\b(his|her|His|Her)\b',
        'pronouns_himself_herself': r'\b(himself|herself|Himself|Herself)\b',
        'titles_mr_mrs': r'\b(Mr\.|Mrs\.|Ms\.|Miss)\b',
        'gendered_words': r'\b(man|woman|boy|girl|male|female|gentleman|lady|sir|madam|husband|wife|father|mother|son|daughter|brother|sister|uncle|aunt|nephew|niece|king|queen|prince|princess|duke|duchess|lord|lady|master|mistress)\b',
        'neutral_pronouns': r'\b(they|them|their|They|Them|Their)\b',
        'neutral_titles': r'\b(Mx\.)\b'
    }
    
    results = {}
    for category, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        results[category] = {
            'count': len(matches),
            'examples': list(set(matches))[:10]  # First 10 unique examples
        }
    
    return results

def spot_check_samples(original_text, transformed_text, num_samples=20, sample_size=500):
    """Perform spot checks on random samples of the text."""
    
    print(f"🔍 SPOT CHECK: Analyzing {num_samples} random samples...")
    
    max_start = min(len(original_text), len(transformed_text)) - sample_size
    if max_start <= 0:
        print("❌ Text too short for sampling")
        return []
    
    issues = []
    
    for i in range(num_samples):
        # Get random position
        start_pos = random.randint(0, max_start)
        end_pos = start_pos + sample_size
        
        orig_sample = original_text[start_pos:end_pos]
        trans_sample = transformed_text[start_pos:end_pos] if end_pos <= len(transformed_text) else transformed_text[start_pos:]
        
        # Check for obvious issues
        if 'he ' in trans_sample.lower() or 'she ' in trans_sample.lower():
            # Find the specific instance
            for match in re.finditer(r'\b(he|she)\b', trans_sample, re.IGNORECASE):
                context_start = max(0, match.start() - 50)
                context_end = min(len(trans_sample), match.end() + 50)
                context = trans_sample[context_start:context_end]
                issues.append({
                    'type': 'untransformed_pronoun',
                    'position': start_pos + match.start(),
                    'found': match.group(),
                    'context': context.strip()
                })
        
        if 'Mr.' in trans_sample or 'Mrs.' in trans_sample or 'Ms.' in trans_sample:
            for match in re.finditer(r'\b(Mr\.|Mrs\.|Ms\.)\b', trans_sample):
                context_start = max(0, match.start() - 50)
                context_end = min(len(trans_sample), match.end() + 50)
                context = trans_sample[context_start:context_end]
                issues.append({
                    'type': 'untransformed_title',
                    'position': start_pos + match.start(),
                    'found': match.group(),
                    'context': context.strip()
                })
    
    return issues

def check_transformation_completeness(original_text, transformed_text):
    """Check overall transformation completeness."""
    
    print("📊 TRANSFORMATION COMPLETENESS CHECK")
    print("=" * 60)
    
    # Analyze both texts
    orig_analysis = analyze_gendered_language(original_text)
    trans_analysis = analyze_gendered_language(transformed_text)
    
    # Calculate transformation rates
    results = {}
    
    # Check pronoun transformation
    orig_gendered_pronouns = (orig_analysis['pronouns_he_she']['count'] + 
                            orig_analysis['pronouns_him_her']['count'] + 
                            orig_analysis['pronouns_his_her']['count'])
    
    trans_gendered_pronouns = (trans_analysis['pronouns_he_she']['count'] + 
                             trans_analysis['pronouns_him_her']['count'] + 
                             trans_analysis['pronouns_his_her']['count'])
    
    trans_neutral_pronouns = trans_analysis['neutral_pronouns']['count']
    
    # Check title transformation  
    orig_gendered_titles = orig_analysis['titles_mr_mrs']['count']
    trans_gendered_titles = trans_analysis['titles_mr_mrs']['count']
    trans_neutral_titles = trans_analysis['neutral_titles']['count']
    
    # Calculate scores
    pronoun_score = max(0, 100 - (trans_gendered_pronouns / max(1, orig_gendered_pronouns) * 100))
    title_score = max(0, 100 - (trans_gendered_titles / max(1, orig_gendered_titles) * 100))
    
    results = {
        'pronoun_transformation': {
            'original_count': orig_gendered_pronouns,
            'remaining_count': trans_gendered_pronouns,
            'neutral_added': trans_neutral_pronouns,
            'score': pronoun_score
        },
        'title_transformation': {
            'original_count': orig_gendered_titles,
            'remaining_count': trans_gendered_titles,
            'neutral_added': trans_neutral_titles,
            'score': title_score
        }
    }
    
    # Print results
    print(f"🔤 PRONOUN TRANSFORMATION:")
    print(f"   Original gendered pronouns: {orig_gendered_pronouns}")
    print(f"   Remaining gendered pronouns: {trans_gendered_pronouns}")
    print(f"   Neutral pronouns added: {trans_neutral_pronouns}")
    print(f"   Transformation score: {pronoun_score:.1f}%")
    
    if trans_gendered_pronouns > 0:
        print(f"   ⚠️ Examples of remaining: {trans_analysis['pronouns_he_she']['examples'][:5]}")
    
    print(f"\n👤 TITLE TRANSFORMATION:")
    print(f"   Original gendered titles: {orig_gendered_titles}")
    print(f"   Remaining gendered titles: {trans_gendered_titles}")
    print(f"   Neutral titles added: {trans_neutral_titles}")
    print(f"   Transformation score: {title_score:.1f}%")
    
    if trans_gendered_titles > 0:
        print(f"   ⚠️ Examples of remaining: {trans_analysis['titles_mr_mrs']['examples'][:5]}")
    
    # Overall score
    overall_score = (pronoun_score + title_score) / 2
    print(f"\n🎯 OVERALL TRANSFORMATION SCORE: {overall_score:.1f}%")
    
    if overall_score >= 95:
        print("✅ EXCELLENT transformation quality!")
    elif overall_score >= 85:
        print("👍 GOOD transformation quality")
    elif overall_score >= 70:
        print("⚠️ FAIR transformation quality - some issues detected")
    else:
        print("❌ POOR transformation quality - significant issues")
    
    return results

def validate_text_integrity(original_text, transformed_text):
    """Check that text structure and content integrity is maintained."""
    
    print(f"\n🔧 TEXT INTEGRITY CHECK")
    print("=" * 60)
    
    issues = []
    
    # Length check
    length_ratio = len(transformed_text) / len(original_text)
    print(f"📏 Length ratio: {length_ratio:.3f}")
    
    if length_ratio < 0.8 or length_ratio > 1.3:
        issues.append(f"Significant length change: {length_ratio:.3f}")
        print("❌ Significant length change detected")
    else:
        print("✅ Length preserved well")
    
    # Chapter preservation check
    orig_chapters = len(re.findall(r'CHAPTER [LXIVCDM]+', original_text))
    trans_chapters = len(re.findall(r'CHAPTER [LXIVCDM]+', transformed_text))
    
    print(f"📖 Chapters: {orig_chapters} → {trans_chapters}")
    
    if orig_chapters != trans_chapters:
        issues.append(f"Chapter count mismatch: {orig_chapters} → {trans_chapters}")
        print("❌ Chapter structure altered")
    else:
        print("✅ Chapter structure preserved")
    
    # Paragraph structure check
    orig_paragraphs = original_text.count('\n\n')
    trans_paragraphs = transformed_text.count('\n\n')
    
    print(f"📄 Paragraph breaks: {orig_paragraphs} → {trans_paragraphs}")
    
    para_ratio = trans_paragraphs / max(1, orig_paragraphs)
    if para_ratio < 0.9 or para_ratio > 1.1:
        issues.append(f"Paragraph structure altered: {para_ratio:.3f}")
        print("⚠️ Paragraph structure slightly altered")
    else:
        print("✅ Paragraph structure preserved")
    
    return issues

def quick_validation_report(original_file, transformed_file, chunks_transformed=None):
    """Generate a quick validation report for transformed text."""
    
    print("🚀 TRANSFORMATION VALIDATION REPORT")
    print("=" * 80)
    
    # Load files
    try:
        with open(original_file, 'r') as f:
            original_text = f.read()
        
        with open(transformed_file, 'r') as f:
            transformed_text = f.read()
            
        print(f"📁 Original: {original_file} ({len(original_text):,} chars)")
        print(f"📁 Transformed: {transformed_file} ({len(transformed_text):,} chars)")
        
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return False
    
    # If chunks_transformed is specified, validate only that portion
    if chunks_transformed:
        print(f"🎯 Validating first {chunks_transformed} chunks only")
        
        # Get chunk boundaries
        from ai_chunking import chunk_text_ai
        chunks = chunk_text_ai(original_text, prefer_ai=False)
        
        if len(chunks) >= chunks_transformed:
            # Calculate boundary of transformed content
            boundary = sum(chunks[i]['size'] for i in range(chunks_transformed))
            
            # Trim texts to only the transformed portion
            original_text = original_text[:boundary]
            transformed_text = transformed_text[:boundary]
            
            print(f"📊 Focused on first {boundary:,} characters ({chunks_transformed} chunks)")
        else:
            print(f"⚠️ Only {len(chunks)} chunks available, validating all")
    
    # Run validation checks
    transformation_results = check_transformation_completeness(original_text, transformed_text)
    
    integrity_issues = validate_text_integrity(original_text, transformed_text)
    
    spot_check_issues = spot_check_samples(original_text, transformed_text)
    
    # Summary
    print(f"\n📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    pronoun_score = transformation_results['pronoun_transformation']['score']
    title_score = transformation_results['title_transformation']['score']
    overall_score = (pronoun_score + title_score) / 2
    
    print(f"🎯 Overall Score: {overall_score:.1f}%")
    print(f"🔍 Spot Check Issues: {len(spot_check_issues)}")
    print(f"⚠️ Integrity Issues: {len(integrity_issues)}")
    
    if len(spot_check_issues) > 0:
        print(f"\n❌ SPOT CHECK ISSUES FOUND:")
        for issue in spot_check_issues[:5]:  # Show first 5
            print(f"   - {issue['type']}: '{issue['found']}' at position {issue['position']}")
            print(f"     Context: ...{issue['context']}...")
    
    if len(integrity_issues) > 0:
        print(f"\n⚠️ INTEGRITY ISSUES:")
        for issue in integrity_issues:
            print(f"   - {issue}")
    
    # Final grade
    print(f"\n🏆 FINAL GRADE:")
    if overall_score >= 95 and len(spot_check_issues) == 0:
        print("✅ EXCELLENT - Ready for production!")
    elif overall_score >= 85 and len(spot_check_issues) <= 2:
        print("👍 GOOD - Minor issues, mostly ready")
    elif overall_score >= 70:
        print("⚠️ FAIR - Needs refinement")
    else:
        print("❌ POOR - Significant issues, needs work")
    
    return True

def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate gender transformation quality')
    parser.add_argument('original', help='Path to original text file')
    parser.add_argument('transformed', help='Path to transformed text file')
    parser.add_argument('--chunks', '-c', type=int, help='Number of chunks that were transformed (validates only that portion)')
    
    args = parser.parse_args()
    
    quick_validation_report(args.original, args.transformed, args.chunks)

if __name__ == "__main__":
    main()