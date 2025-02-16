"""Test accuracy of character analysis against ground truth."""
import json
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

@dataclass
class MentionMatch:
    """A mention match between predicted and ground truth."""
    predicted_text: str
    predicted_pos: int
    ground_truth_text: str
    ground_truth_pos: int
    distance: int
    is_match: bool

def load_ground_truth(filename: str) -> Dict:
    """Load ground truth data from JSON file."""
    with open(filename) as f:
        return json.load(f)

def calculate_mention_overlap(pred_start: int, pred_end: int,
                           true_start: int, true_end: int) -> float:
    """Calculate overlap between two mentions as percentage."""
    overlap_start = max(pred_start, true_start)
    overlap_end = min(pred_end, true_end)
    if overlap_end <= overlap_start:
        return 0.0
    
    overlap_length = overlap_end - overlap_start
    pred_length = pred_end - pred_start
    true_length = true_end - true_start
    
    return overlap_length / max(pred_length, true_length)

def find_best_match(pred_mention: Dict, true_mentions: List[Dict],
                   max_distance: int = 50) -> Tuple[Dict, float]:
    """Find best matching ground truth mention for a prediction."""
    best_match = None
    best_overlap = 0.0
    
    for true_mention in true_mentions:
        # Calculate position distance
        distance = abs(pred_mention['start'] - true_mention['start'])
        if distance > max_distance:
            continue
            
        # Calculate text overlap
        overlap = calculate_mention_overlap(
            pred_mention['start'], pred_mention['end'],
            true_mention['start'], true_mention['end']
        )
        
        if overlap > best_overlap:
            best_match = true_mention
            best_overlap = overlap
            
    return best_match, best_overlap

def evaluate_character(pred_char: Dict, true_char: Dict,
                      overlap_threshold: float = 0.5) -> Dict:
    """Evaluate predictions for a single character."""
    results = {
        'name_mentions': {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'matches': []
        },
        'pronoun_mentions': {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'matches': []
        }
    }
    
    # Track used ground truth mentions to avoid double-counting
    used_true_mentions = {'name': set(), 'pronoun': set()}
    
    # Check each predicted mention
    for mention in pred_char.get('mentions', []):
        mention_type = 'name_mentions' if mention['type'] == 'name' else 'pronoun_mentions'
        true_mentions = true_char.get(mention_type, [])
        
        # Find best matching ground truth mention
        best_match, overlap = find_best_match(mention, true_mentions)
        
        if best_match and overlap >= overlap_threshold:
            # True positive if not already matched
            if best_match['start'] not in used_true_mentions[mention['type']]:
                results[mention_type]['true_positives'] += 1
                used_true_mentions[mention['type']].add(best_match['start'])
                
                results[mention_type]['matches'].append(MentionMatch(
                    predicted_text=mention['text'],
                    predicted_pos=mention['start'],
                    ground_truth_text=best_match['text'],
                    ground_truth_pos=best_match['start'],
                    distance=abs(mention['start'] - best_match['start']),
                    is_match=True
                ))
            else:
                results[mention_type]['false_positives'] += 1
        else:
            results[mention_type]['false_positives'] += 1
            
            results[mention_type]['matches'].append(MentionMatch(
                predicted_text=mention['text'],
                predicted_pos=mention['start'],
                ground_truth_text='',
                ground_truth_pos=-1,
                distance=-1,
                is_match=False
            ))
    
    # Count false negatives (unmatched ground truth mentions)
    for mention_type in ['name_mentions', 'pronoun_mentions']:
        true_mentions = true_char.get(mention_type, [])
        for true_mention in true_mentions:
            if true_mention['start'] not in used_true_mentions[mention_type.split('_')[0]]:
                results[mention_type]['false_negatives'] += 1
                
                results[mention_type]['matches'].append(MentionMatch(
                    predicted_text='',
                    predicted_pos=-1,
                    ground_truth_text=true_mention['text'],
                    ground_truth_pos=true_mention['start'],
                    distance=-1,
                    is_match=False
                ))
    
    return results

def calculate_metrics(results: Dict) -> Dict:
    """Calculate precision, recall, and F1 score."""
    metrics = {}
    
    for mention_type in ['name_mentions', 'pronoun_mentions']:
        tp = results[mention_type]['true_positives']
        fp = results[mention_type]['false_positives']
        fn = results[mention_type]['false_negatives']
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics[mention_type] = {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
        
    return metrics

def main():
    """Run accuracy evaluation."""
    # Load ground truth
    ground_truth = load_ground_truth('test_data/chapter1_ground_truth.json')
    
    # Load predictions (from most recent test run)
    with open('test_output.json') as f:
        predictions = json.load(f)
    
    # Evaluate each character
    all_results = {}
    for char_name, true_char in ground_truth.items():
        if char_name in predictions:
            results = evaluate_character(predictions[char_name], true_char)
            all_results[char_name] = results
    
    # Calculate overall metrics
    overall_metrics = {
        'name_mentions': {
            'true_positives': sum(r['name_mentions']['true_positives'] for r in all_results.values()),
            'false_positives': sum(r['name_mentions']['false_positives'] for r in all_results.values()),
            'false_negatives': sum(r['name_mentions']['false_negatives'] for r in all_results.values())
        },
        'pronoun_mentions': {
            'true_positives': sum(r['pronoun_mentions']['true_positives'] for r in all_results.values()),
            'false_positives': sum(r['pronoun_mentions']['false_positives'] for r in all_results.values()),
            'false_negatives': sum(r['pronoun_mentions']['false_negatives'] for r in all_results.values())
        }
    }
    
    metrics = calculate_metrics(overall_metrics)
    
    # Print results
    print("\nOverall Metrics:")
    print("Name Mentions:")
    print(f"  Precision: {metrics['name_mentions']['precision']:.2f}")
    print(f"  Recall: {metrics['name_mentions']['recall']:.2f}")
    print(f"  F1: {metrics['name_mentions']['f1']:.2f}")
    
    print("\nPronoun Mentions:")
    print(f"  Precision: {metrics['pronoun_mentions']['precision']:.2f}")
    print(f"  Recall: {metrics['pronoun_mentions']['recall']:.2f}")
    print(f"  F1: {metrics['pronoun_mentions']['f1']:.2f}")
    
    # Print detailed results per character
    print("\nDetailed Results:")
    for char_name, results in all_results.items():
        print(f"\n{char_name}:")
        for mention_type in ['name_mentions', 'pronoun_mentions']:
            print(f"  {mention_type}:")
            print(f"    True Positives: {results[mention_type]['true_positives']}")
            print(f"    False Positives: {results[mention_type]['false_positives']}")
            print(f"    False Negatives: {results[mention_type]['false_negatives']}")
            
            print("\n    Matches:")
            for match in results[mention_type]['matches']:
                if match.is_match:
                    print(f"      ✓ {match.predicted_text} ({match.predicted_pos}) -> {match.ground_truth_text} ({match.ground_truth_pos})")
                else:
                    if match.predicted_text:
                        print(f"      ✗ {match.predicted_text} ({match.predicted_pos}) -> No match")
                    else:
                        print(f"      ✗ Missed: {match.ground_truth_text} ({match.ground_truth_pos})")

if __name__ == '__main__':
    main()
