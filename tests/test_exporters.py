"""Tests for src.exporters."""

import json
import tempfile
from pathlib import Path

import pytest

from src.exporters import (
    FORMATS,
    _book_author,
    _book_title,
    _italicize_markup,
    _paragraph_text,
    export_book,
    export_plain_ascii,
    export_plain_text,
    export_plain_text_italics,
    load_transformed_json,
)


def _make_sample_json(path: str, title: str = "Test Book", author: str = "Test Author") -> None:
    """Write a minimal transformed book JSON (app format: metadata + chapters with sentences)."""
    data = {
        "metadata": {"title": title, "author": author},
        "chapters": [
            {
                "number": 1,
                "title": "Chapter One",
                "paragraphs": [{"sentences": ["First sentence.", "Second sentence."]}],
            },
            {
                "number": 2,
                "title": "Chapter Two",
                "paragraphs": [
                    {"sentences": ["Only _emphasis_ here."]},
                ],
            },
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def test_book_title_from_metadata():
    """Title is read from metadata when not at top level."""
    data = {"metadata": {"title": "Pride and Prejudice", "author": "Austen"}}
    assert _book_title(data) == "Pride and Prejudice"


def test_book_title_top_level():
    """Title at top level is used."""
    data = {"title": "Top Title", "metadata": {"title": "Meta Title"}}
    assert _book_title(data) == "Top Title"


def test_book_author_from_metadata():
    """Author is read from metadata when not at top level."""
    data = {"metadata": {"author": "Jane Austen"}}
    assert _book_author(data) == "Jane Austen"


def test_paragraph_text_from_sentences():
    """Paragraph text comes from sentences list (app format)."""
    para = {"sentences": ["Hello.", "World."]}
    assert _paragraph_text(para) == "Hello. World."


def test_paragraph_text_from_transformed_text():
    """Paragraph text falls back to transformed_text or text."""
    assert _paragraph_text({"transformed_text": "One"}) == "One"
    assert _paragraph_text({"text": "Two"}) == "Two"


def test_italicize_markup():
    """_word_ is converted to <i>word</i>."""
    assert _italicize_markup("Say _him_ again.") == "Say <i>him</i> again."


def test_formats_registry():
    """All expected export formats are registered."""
    assert "txt" in FORMATS
    assert "ascii" in FORMATS
    assert "txt_italics" in FORMATS
    assert "rtf" in FORMATS
    for info in FORMATS.values():
        assert "exporter" in info
        assert callable(info["exporter"])


def test_load_and_export_roundtrip(tmp_path):
    """Load JSON and export to txt, ascii, and italics without error."""
    json_path = tmp_path / "book.json"
    _make_sample_json(str(json_path))

    data = load_transformed_json(str(json_path))
    assert _book_title(data) == "Test Book"
    assert _book_author(data) == "Test Author"

    out_txt = export_plain_text(str(json_path), str(tmp_path / "out.txt"))
    assert Path(out_txt).exists()
    content = Path(out_txt).read_text(encoding="utf-8")
    assert "TEST BOOK" in content
    assert "First sentence" in content

    out_ascii = export_plain_ascii(str(json_path))
    assert Path(out_ascii).exists()
    assert out_ascii.endswith(".ascii.txt")

    out_italics = export_plain_text_italics(str(json_path))
    assert Path(out_italics).exists()
    assert "<i>emphasis</i>" in Path(out_italics).read_text(encoding="utf-8")


def test_export_book_dispatches(tmp_path):
    """export_book dispatches to correct exporter."""
    json_path = tmp_path / "book.json"
    _make_sample_json(str(json_path))

    for key in ("txt", "ascii", "txt_italics", "rtf"):
        out = export_book(str(json_path), key)
        assert Path(out).exists()


def test_export_book_unknown_format():
    """export_book raises for unknown format."""
    with pytest.raises(ValueError, match="Unknown format"):
        export_book("/nonexistent.json", "invalid_key")
