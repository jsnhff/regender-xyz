"""Logging functionality with improved formatting."""

import os
from datetime import datetime
from typing import Any, Optional
import difflib
from pathlib import Path

from config.constants import DEFAULT_LOG_DIR

class Logger:
    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = None

    def _generate_log_filename(self) -> Path:
        """Generate unique log filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.log_dir / f"log_{timestamp}.txt"

    def log_output(self, original_text: str, regendered_text: str) -> None:
        """
        Log original and regendered text with improved formatting.
        
        Args:
            original_text: The original input text
            regendered_text: The regendered output text
        """
        self.current_log_file = self._generate_log_filename()
        
        with open(self.current_log_file, 'w', encoding='utf-8') as file:
            # Write original text with proper line breaks
            file.write(original_text.strip())
            file.write("\n\n")  # Add space between sections
            
            # Write the character changes section
            file.write("Character Changes:\n")
            # Note: We'll need to implement character_changes tracking
            file.write("=" * 50)
            file.write("\n\n")
            
            # Write regendered text with proper line breaks
            file.write(regendered_text.strip())
            file.write("\n\n")
            
            # Write the diff in a more readable format
            file.write("Detailed Changes:\n")
            file.write("=" * 50)
            file.write("\n")
            
            diff = list(difflib.unified_diff(
                original_text.splitlines(),
                regendered_text.splitlines(),
                fromfile='Original',
                tofile='Regendered',
                lineterm=''
            ))
            
            # Format the diff output
            for line in diff:
                if line.startswith('+++') or line.startswith('---'):
                    continue  # Skip the file names in diff output
                if line.startswith('-'):
                    file.write(f"REMOVED: {line[1:]}\n")
                elif line.startswith('+'):
                    file.write(f"ADDED:   {line[1:]}\n")
                elif line.startswith('@@'):
                    file.write(f"\nChange Block:\n{line}\n")
                else:
                    file.write(f"CONTEXT: {line}\n")

    def get_current_log_path(self) -> Optional[Path]:
        """Get path of current log file."""
        return self.current_log_file