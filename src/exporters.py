"""
Export Formats for Regender

Converts transformed JSON output to various formats:
- Plain text (.txt) UTF-8
- Plain text ASCII (for InDesign, avoids UTF-8 import issues)
- Plain text with italics markup (_word_ → <i>word</i>) for InDesign character styles
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


def _book_title(data: dict) -> Optional[str]:
    """Get book title from JSON (top-level or metadata)."""
    return data.get("title") or (data.get("metadata") or {}).get("title")


def _book_author(data: dict) -> Optional[str]:
    """Get book author from JSON (top-level or metadata)."""
    return data.get("author") or (data.get("metadata") or {}).get("author")


def _paragraph_text(para: dict) -> str:
    """Get paragraph text from JSON (sentences, transformed_text, or text)."""
    if "sentences" in para:
        return " ".join(para["sentences"]) if para["sentences"] else ""
    return para.get("transformed_text") or para.get("text", "")


def _italicize_markup(text: str) -> str:
    """Replace _word_ with <i>word</i> for InDesign character styles."""
    return re.sub(r"_([^_]+)_", r"<i>\1</i>", text)


def export_plain_text(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Export transformed book to plain text (UTF-8).
    """
    return _export_plain_impl(json_path, output_path, encoding="utf-8", use_italics_markup=False)


def export_plain_ascii(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Export as plain ASCII for InDesign (avoids UTF-8 import issues).
    Non-ASCII characters are replaced with '?'.
    """
    return _export_plain_impl(
        json_path,
        output_path,
        encoding="ascii",
        errors="replace",
        use_italics_markup=False,
        suffix=".ascii.txt",
    )


def export_plain_text_italics(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Export plain text with _word_ → <i>word</i> for InDesign character styles.
    """
    return _export_plain_impl(
        json_path,
        output_path,
        encoding="utf-8",
        use_italics_markup=True,
        suffix=".italics.txt",
    )


def _export_plain_impl(
    json_path: str,
    output_path: Optional[str] = None,
    encoding: str = "utf-8",
    errors: str = "strict",
    use_italics_markup: bool = False,
    suffix: str = ".txt",
) -> str:
    """Shared implementation for plain text exports."""
    data = load_transformed_json(json_path)

    if output_path is None:
        output_path = str(Path(json_path).with_suffix(suffix))

    lines = []
    title = _book_title(data)
    author = _book_author(data)

    if title:
        lines.append(title.upper())
        lines.append("")
        lines.append("")
    if author:
        lines.append(f"by {author}")
        lines.append("")
        lines.append("")

    chapters = data.get("chapters", [])
    for chapter in chapters:
        if chapter.get("title"):
            lines.append("")
            lines.append(chapter["title"].upper())
            lines.append("")
        for para in chapter.get("paragraphs", []):
            text = _paragraph_text(para)
            if text.strip():
                if use_italics_markup:
                    text = _italicize_markup(text)
                lines.append(text)
                lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding=encoding, errors=errors) as f:
        f.write(content)
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
    rtf_lines = [
        "{\\rtf1\\ansi\\ansicpg1252\\deff0",
        "{\\fonttbl{\\f0\\froman Times New Roman;}{\\f1\\fswiss Helvetica;}}",
        "{\\colortbl;\\red0\\green0\\blue0;}",
        "\\paperw12240\\paperh15840",
        "\\margl1440\\margr1440\\margt1440\\margb1440",
        "\\widowctrl\\ftnbj\\aenddoc",
        "\\pard\\plain\\f0\\fs24",
        "",
    ]

    title = _book_title(data)
    author = _book_author(data)
    if title:
        rtf_lines.append(f"\\pard\\qc\\b\\fs36 {_escape_rtf(title.upper())}\\b0\\par")
        rtf_lines.append("\\par")
    if author:
        rtf_lines.append(f"\\pard\\qc\\i {_escape_rtf('by ' + author)}\\i0\\par")
        rtf_lines.append("\\par\\par")
    rtf_lines.append("\\pard\\ql\\fs24")

    chapters = data.get("chapters", [])
    for i, chapter in enumerate(chapters):
        if chapter.get("title"):
            rtf_lines.append("\\par")
            rtf_lines.append(
                f"\\pard\\qc\\b\\fs28 {_escape_rtf(chapter['title'].upper())}\\b0\\par"
            )
            rtf_lines.append("\\pard\\ql\\fs24\\par")
        for para in chapter.get("paragraphs", []):
            text = _paragraph_text(para)
            if text.strip():
                rtf_lines.append(f"\\fi720 {_escape_rtf(text)}\\par")

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
        "description": "UTF-8 text file",
        "exporter": export_plain_text,
    },
    "ascii": {
        "name": "Plain ASCII",
        "extension": ".txt",
        "description": "ASCII only (InDesign-safe, no UTF-8 issues)",
        "exporter": export_plain_ascii,
    },
    "txt_italics": {
        "name": "Plain Text + Italics",
        "extension": ".txt",
        "description": "_word_ → <i>word</i> for InDesign character styles",
        "exporter": export_plain_text_italics,
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
        format_key: Format key (txt, ascii, txt_italics, rtf)
        output_path: Optional output path

    Returns:
        Path to the exported file
    """
    if format_key not in FORMATS:
        raise ValueError(f"Unknown format: {format_key}. Available: {list(FORMATS.keys())}")

    exporter = FORMATS[format_key]["exporter"]
    return exporter(json_path, output_path)
