"""Export character data to various formats."""

import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


def save_character_analysis(characters: Dict[str, Any], 
                          output_path: str,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
    """Save character analysis to a JSON file.
    
    Args:
        characters: Character data
        output_path: Path to save the file
        metadata: Optional metadata to include
    """
    data = {
        "characters": characters,
        "metadata": metadata or {
            "total_characters": len(characters),
            "analysis_date": _get_current_date()
        }
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_characters_to_csv(characters: Dict[str, Any], 
                           output_path: str) -> None:
    """Export character list to CSV format.
    
    Args:
        characters: Character data
        output_path: Path to save the CSV file
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Name', 'Gender', 'Role', 'Mentions', 'Variants'])
        
        # Write character data
        for name, info in sorted(characters.items()):
            writer.writerow([
                name,
                info.get('gender', 'unknown'),
                info.get('role', ''),
                len(info.get('mentions', [])) or info.get('mentions', 0),
                ', '.join(info.get('name_variants', []))
            ])


def export_character_graph(characters: Dict[str, Any], 
                         output_path: str,
                         include_relationships: bool = True) -> None:
    """Export character relationship graph in JSON format.
    
    Args:
        characters: Character data
        output_path: Path to save the graph file
        include_relationships: Whether to analyze relationships
    """
    # Build nodes
    nodes = []
    for name, info in characters.items():
        node = {
            "id": name,
            "label": name,
            "gender": info.get('gender', 'unknown'),
            "mentions": len(info.get('mentions', [])) or info.get('mentions', 0),
            "role": info.get('role', '')
        }
        nodes.append(node)
    
    # Build edges (relationships)
    edges = []
    if include_relationships:
        relationships = _extract_relationships(characters)
        edge_id = 0
        for (char1, char2), strength in relationships.items():
            edges.append({
                "id": edge_id,
                "source": char1,
                "target": char2,
                "weight": strength,
                "type": "co-occurrence"
            })
            edge_id += 1
    
    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_characters": len(nodes),
            "total_relationships": len(edges),
            "graph_type": "character_network"
        }
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)


def _extract_relationships(characters: Dict[str, Any]) -> Dict[tuple, int]:
    """Extract character relationships based on co-occurrence.
    
    This is a simple implementation that counts how often characters
    appear in the same contexts. A more sophisticated version could
    analyze actual interactions.
    """
    relationships = defaultdict(int)
    
    # For each character, look at their mentions
    for name1, info1 in characters.items():
        mentions1 = info1.get('mentions', [])
        if not mentions1:
            continue
            
        # Compare with other characters
        for name2, info2 in characters.items():
            if name1 >= name2:  # Avoid duplicates
                continue
                
            mentions2 = info2.get('mentions', [])
            if not mentions2:
                continue
            
            # Count co-occurrences (simplified: same context)
            co_occurrences = 0
            for m1 in mentions1:
                context1 = m1.get('context', '')
                for m2 in mentions2:
                    context2 = m2.get('context', '')
                    # If contexts overlap, they co-occur
                    if context1 and context2 and (
                        context1 in context2 or context2 in context1
                    ):
                        co_occurrences += 1
            
            if co_occurrences > 0:
                relationships[(name1, name2)] = co_occurrences
    
    return dict(relationships)


def create_character_summary(characters: Dict[str, Any]) -> str:
    """Create a human-readable summary of characters.
    
    Args:
        characters: Character data
        
    Returns:
        Formatted summary string
    """
    if not characters:
        return "No characters found."
    
    lines = ["# Character Summary\n"]
    
    # Sort by mentions (most important first)
    sorted_chars = sorted(
        characters.items(),
        key=lambda x: len(x[1].get('mentions', [])) or x[1].get('mentions', 0),
        reverse=True
    )
    
    # Stats
    total_chars = len(characters)
    male_chars = sum(1 for _, info in characters.items() if info.get('gender') == 'male')
    female_chars = sum(1 for _, info in characters.items() if info.get('gender') == 'female')
    unknown_chars = total_chars - male_chars - female_chars
    
    lines.append(f"Total Characters: {total_chars}")
    lines.append(f"- Male: {male_chars}")
    lines.append(f"- Female: {female_chars}")
    lines.append(f"- Unknown: {unknown_chars}")
    lines.append("\n## Main Characters\n")
    
    # List top characters
    for i, (name, info) in enumerate(sorted_chars[:10]):
        mentions = len(info.get('mentions', [])) or info.get('mentions', 0)
        gender = info.get('gender', 'unknown')
        role = info.get('role', 'N/A')
        
        lines.append(f"{i+1}. **{name}** ({gender})")
        lines.append(f"   - Mentions: {mentions}")
        lines.append(f"   - Role: {role}")
        
        variants = info.get('name_variants', [])
        if variants:
            lines.append(f"   - Also known as: {', '.join(variants)}")
        
        lines.append("")
    
    return '\n'.join(lines)


def _get_current_date() -> str:
    """Get current date as ISO string."""
    from datetime import datetime
    return datetime.now().isoformat()