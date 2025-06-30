"""
Common utilities for Gutenberg processing
"""

import re
import os
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[,]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if needed"""
    directory = Path(path)
    directory.mkdir(exist_ok=True, parents=True)
    return directory


def format_size(bytes: int) -> str:
    """Format bytes as human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def print_progress(current: int, total: int, prefix: str = "Progress"):
    """Print a simple progress indicator"""
    percent = (current / total) * 100 if total > 0 else 0
    print(f"\r{prefix}: {current}/{total} ({percent:.1f}%)", end='', flush=True)
    if current == total:
        print()  # New line when complete