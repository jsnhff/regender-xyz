"""Special detector for play formats, including non-standard ones."""

import re
from typing import List, Tuple, Optional, Dict
from ..patterns.base import PatternType
from .section_detector import DetectedSection


class PlayFormatDetector:
    """Detects and handles special play formats."""
    
    def detect_importance_of_being_earnest_format(self, lines: List[str]) -> Optional[List[DetectedSection]]:
        """
        Detect the specific format used in The Importance of Being Earnest where:
        - Acts are listed at the beginning (e.g., "ACT I. Location")
        - Actual acts are marked by bare "SCENE" markers
        - Character dialogue uses "CHARACTER." format
        """
        # Look for act titles at the beginning
        act_titles = []
        act_title_pattern = re.compile(r'^ACT\s+([IVX]+)\.\s*(.*)$')
        
        for i in range(min(100, len(lines))):  # Check first 100 lines
            match = act_title_pattern.match(lines[i].strip())
            if match:
                act_titles.append({
                    'number': match.group(1),
                    'title': lines[i].strip(),
                    'line': i
                })
        
        if not act_titles:
            return None
            
        # Find SCENE markers that indicate actual act starts
        scene_markers = []
        for i, line in enumerate(lines):
            if line.strip() == 'SCENE':
                scene_markers.append(i)
        
        # If we have act titles and matching SCENE markers, this is our format
        if len(scene_markers) >= len(act_titles):
            sections = []
            
            for idx, marker in enumerate(scene_markers[:len(act_titles)]):
                # Determine act end
                if idx < len(scene_markers) - 1:
                    end_line = scene_markers[idx + 1]
                else:
                    # Find end of play (PROJECT GUTENBERG markers)
                    end_line = len(lines)
                    for i in range(marker, len(lines)):
                        if 'END OF THE PROJECT GUTENBERG' in lines[i] or 'END OF THIS PROJECT GUTENBERG' in lines[i]:
                            end_line = i
                            break
                
                # Create section for this act
                act_title = act_titles[idx]['title'] if idx < len(act_titles) else f"ACT {idx + 1}"
                section = DetectedSection(
                    pattern_type=PatternType.ACT,
                    start_line=marker,
                    end_line=end_line,
                    title=act_title,
                    number=act_titles[idx]['number'] if idx < len(act_titles) else str(idx + 1),
                    content_lines=lines[marker:end_line]
                )
                sections.append(section)
            
            return sections
        
        return None
    
    def is_play_dialogue_line(self, line: str) -> bool:
        """Check if a line is character dialogue (e.g., 'ALGERNON.')"""
        # Match uppercase name followed by period
        return bool(re.match(r'^[A-Z][A-Z]+\.$', line.strip()))
    
    def extract_character_from_dialogue(self, line: str) -> Optional[str]:
        """Extract character name from dialogue line."""
        match = re.match(r'^([A-Z][A-Z]+)\.$', line.strip())
        return match.group(1) if match else None