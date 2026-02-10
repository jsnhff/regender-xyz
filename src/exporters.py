"""
Export Formats for Regender

Converts transformed JSON output to various formats:
- Plain text (.txt)
- RTF with UTF-8 encoding (for InDesign)
"""

import json
import re
from pathlib import Path
from typing import Optional


def load_transformed_json(json_path: str) -> dict:
    """Load a transformed book JSON file."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def export_plain_text(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Export transformed book to plain text.

    Args:
        json_path: Path to the transformed JSON file
        output_path: Optional output path (defaults to same name with .txt)

    Returns:
        Path to the exported file
    """
    data = load_transformed_json(json_path)

    if output_path is None:
        output_path = str(Path(json_path).with_suffix(".txt"))

    lines = []

    # Title
    if data.get("title"):
        lines.append(data["title"].upper())
        lines.append("")
        lines.append("")

    # Author
    if data.get("author"):
        lines.append(f"by {data['author']}")
        lines.append("")
        lines.append("")

    # Chapters
    chapters = data.get("chapters", [])
    for chapter in chapters:
        # Chapter heading
        if chapter.get("title"):
            lines.append("")
            lines.append(chapter["title"].upper())
            lines.append("")

        # Paragraphs
        paragraphs = chapter.get("paragraphs", [])
        for para in paragraphs:
            # Get transformed text if available, otherwise original
            text = para.get("transformed_text") or para.get("text", "")
            if text.strip():
                lines.append(text)
                lines.append("")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def _escape_rtf(text: str) -> str:
    """
    Escape text for RTF format with proper UTF-8 encoding.

    RTF uses \\uN? notation for Unicode characters where N is the decimal code point.
    """
    result = []
    for char in text:
        code = ord(char)
        if code < 128:
            # ASCII characters - escape special RTF chars
            if char == "\\":
                result.append("\\\\")
            elif char == "{":
                result.append("\\{")
            elif char == "}":
                result.append("\\}")
            elif char == "\n":
                result.append("\\par\n")
            elif char == "\t":
                result.append("\\tab ")
            else:
                result.append(char)
        else:
            # Unicode character - use \uN? format
            # The ? is a placeholder for non-Unicode readers
            result.append(f"\\u{code}?")

    return "".join(result)


def export_rtf(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Export transformed book to RTF with UTF-8 encoding.

    This format is optimized for InDesign import with proper Unicode support.

    Args:
        json_path: Path to the transformed JSON file
        output_path: Optional output path (defaults to same name with .rtf)

    Returns:
        Path to the exported file
    """
    data = load_transformed_json(json_path)

    if output_path is None:
        output_path = str(Path(json_path).with_suffix(".rtf"))

    # RTF header with UTF-8 support
    # \ansi\ansicpg1252 is standard, \deff0 sets default font
    # We use Unicode escapes for non-ASCII characters
    rtf_lines = [
        "{\\rtf1\\ansi\\ansicpg1252\\deff0",
        # Font table
        "{\\fonttbl{\\f0\\froman Times New Roman;}{\\f1\\fswiss Helvetica;}}",
        # Color table (black)
        "{\\colortbl;\\red0\\green0\\blue0;}",
        # Document settings
        "\\paperw12240\\paperh15840",  # Letter size
        "\\margl1440\\margr1440\\margt1440\\margb1440",  # 1 inch margins
        "\\widowctrl\\ftnbj\\aenddoc",
        # Default paragraph formatting
        "\\pard\\plain\\f0\\fs24",  # Times, 12pt
        "",
    ]

    # Title
    if data.get("title"):
        title = _escape_rtf(data["title"].upper())
        rtf_lines.append(f"\\pard\\qc\\b\\fs36 {title}\\b0\\par")
        rtf_lines.append("\\par")

    # Author
    if data.get("author"):
        author = _escape_rtf(f"by {data['author']}")
        rtf_lines.append(f"\\pard\\qc\\i {author}\\i0\\par")
        rtf_lines.append("\\par\\par")

    # Reset to left-aligned body text
    rtf_lines.append("\\pard\\ql\\fs24")

    # Chapters
    chapters = data.get("chapters", [])
    for i, chapter in enumerate(chapters):
        # Chapter heading
        if chapter.get("title"):
            chapter_title = _escape_rtf(chapter["title"].upper())
            rtf_lines.append("\\par")
            rtf_lines.append(f"\\pard\\qc\\b\\fs28 {chapter_title}\\b0\\par")
            rtf_lines.append("\\pard\\ql\\fs24\\par")

        # Paragraphs
        paragraphs = chapter.get("paragraphs", [])
        for para in paragraphs:
            # Get transformed text if available, otherwise original
            text = para.get("transformed_text") or para.get("text", "")
            if text.strip():
                escaped = _escape_rtf(text)
                rtf_lines.append(f"\\fi720 {escaped}\\par")  # First line indent

        # Page break between chapters (except last)
        if i < len(chapters) - 1:
            rtf_lines.append("\\page")

    # Close RTF
    rtf_lines.append("}")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rtf_lines))

    return output_path


# Format registry
FORMATS = {
    "txt": {
        "name": "Plain Text",
        "extension": ".txt",
        "description": "Simple UTF-8 text file",
        "exporter": export_plain_text,
    },
    "rtf": {
        "name": "Rich Text Format",
        "extension": ".rtf",
        "description": "RTF with UTF-8 for InDesign",
        "exporter": export_rtf,
    },
}


def export_book(json_path: str, format_key: str, output_path: Optional[str] = None) -> str:
    """
    Export a transformed book to the specified format.

    Args:
        json_path: Path to the transformed JSON file
        format_key: Format key (txt, rtf)
        output_path: Optional output path

    Returns:
        Path to the exported file
    """
    if format_key not in FORMATS:
        raise ValueError(f"Unknown format: {format_key}. Available: {list(FORMATS.keys())}")

    exporter = FORMATS[format_key]["exporter"]
    return exporter(json_path, output_path)
