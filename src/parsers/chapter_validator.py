"""
Chapter Validation and Cleanup

Merges empty chapters and validates chapter structure.
"""

from typing import Any, Dict, List


def validate_and_clean_chapters(
    chapters: list[dict[str, Any]], min_paragraphs: int = 3
) -> list[dict[str, Any]]:
    """
    Validate and clean up chapter list.

    - Merges consecutive empty chapters
    - Removes chapters with no content
    - Renumbers chapters sequentially

    Args:
        chapters: List of chapter dictionaries
        min_paragraphs: Minimum paragraphs for a valid chapter

    Returns:
        Cleaned list of chapters
    """
    if not chapters:
        return []

    cleaned = []
    current_content = []
    current_title = None

    for ch in chapters:
        para_count = len(ch.get("paragraphs", []))

        if para_count >= min_paragraphs:
            # This is a real chapter with content
            if current_content:
                # Save any accumulated content first
                cleaned.append(
                    {
                        "number": len(cleaned) + 1,
                        "title": current_title or f"Chapter {len(cleaned) + 1}",
                        "paragraphs": current_content,
                        "type": "chapter",
                    }
                )
                current_content = []
                current_title = None

            # Add this chapter
            cleaned.append(
                {
                    "number": len(cleaned) + 1,
                    "title": ch.get("title", f"Chapter {len(cleaned) + 1}"),
                    "paragraphs": ch.get("paragraphs", []),
                    "type": ch.get("type", "chapter"),
                    "metadata": ch.get("metadata", {}),
                }
            )
        else:
            # Empty or very small chapter - accumulate its content
            if para_count > 0:
                current_content.extend(ch.get("paragraphs", []))
                if not current_title and ch.get("title"):
                    current_title = ch["title"]

    # Don't forget remaining content
    if current_content:
        cleaned.append(
            {
                "number": len(cleaned) + 1,
                "title": current_title or f"Chapter {len(cleaned) + 1}",
                "paragraphs": current_content,
                "type": "chapter",
            }
        )

    # If we have no valid chapters but have content, create single chapter
    if not cleaned and chapters:
        all_paragraphs = []
        for ch in chapters:
            all_paragraphs.extend(ch.get("paragraphs", []))

        if all_paragraphs:
            cleaned = [
                {"number": 1, "title": "Chapter 1", "paragraphs": all_paragraphs, "type": "chapter"}
            ]

    return cleaned


def is_collection(chapters: list[dict[str, Any]]) -> bool:
    """
    Detect if this looks like a collection (many acts/scenes).

    Shakespeare Complete Works has ~1900 acts/scenes that should
    be grouped into plays.
    """
    if len(chapters) < 100:
        return False

    # Count how many are acts or scenes
    act_scene_count = 0
    for ch in chapters:
        title = ch.get("title", "").lower()
        if "act " in title or "scene " in title:
            act_scene_count += 1

    # If >50% are acts/scenes, it's probably a collection
    return act_scene_count > len(chapters) * 0.5
