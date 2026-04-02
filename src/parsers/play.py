"""
Play Format Parser

Specialized parser for theatrical plays with acts, scenes, and dialogue.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PlayElementType(Enum):
    """Types of play elements."""

    TITLE = "title"
    DRAMATIS_PERSONAE = "dramatis_personae"
    PROLOGUE = "prologue"
    ACT = "act"
    SCENE = "scene"
    STAGE_DIRECTION = "stage_direction"
    CHARACTER_NAME = "character"
    DIALOGUE = "dialogue"
    EPILOGUE = "epilogue"


@dataclass
class PlayElement:
    """A single element in a play."""

    type: PlayElementType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    """A scene in a play."""

    number: str
    title: Optional[str]
    location: Optional[str]
    elements: list[PlayElement] = field(default_factory=list)

    def to_paragraphs(self) -> list[str]:
        """Convert scene to paragraph format for compatibility."""
        paragraphs = []
        current_para = []

        for element in self.elements:
            if element.type == PlayElementType.DIALOGUE:
                # Add character name and dialogue
                if element.metadata.get("character"):
                    current_para.append(f"{element.metadata['character']}: {element.content}")
                else:
                    current_para.append(element.content)
            elif element.type == PlayElementType.STAGE_DIRECTION:
                # Add stage direction as separate paragraph
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
                paragraphs.append(f"[{element.content}]")
            else:
                # Other elements
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
                if element.content:
                    paragraphs.append(element.content)

        if current_para:
            paragraphs.append(" ".join(current_para))

        return paragraphs


@dataclass
class Act:
    """An act in a play."""

    number: str
    title: Optional[str]
    scenes: list[Scene] = field(default_factory=list)


@dataclass
class Play:
    """A complete play structure."""

    title: Optional[str]
    author: Optional[str]
    dramatis_personae: Optional[list[str]]
    prologue: Optional[list[str]]
    acts: list[Act]
    epilogue: Optional[list[str]]


class PlayParser:
    """
    Parser for theatrical plays.

    Handles:
    - Acts and scenes
    - Character dialogue
    - Stage directions
    - Prologues and epilogues
    """

    def parse(self, lines: list[str]) -> Play:
        """
        Parse play text into structured format.

        Args:
            lines: Cleaned text lines (after Gutenberg cleaning)

        Returns:
            Structured Play object
        """
        # Skip TOC if present
        content_start = self._skip_toc(lines)
        lines = lines[content_start:]

        # Initialize play structure
        play = Play(
            title=None, author=None, dramatis_personae=None, prologue=None, acts=[], epilogue=None
        )

        # Parse the play
        self._parse_content(lines, play)

        return play

    def _skip_toc(self, lines: list[str]) -> int:
        """
        Skip table of contents to find actual play content.

        Look for duplicate act/scene markers.
        """
        # Find all Act I markers
        act_one_positions = []
        for i, line in enumerate(lines[:500]):
            line_upper = line.upper().strip()
            if "ACT I" in line_upper and "SCENE" not in line_upper:
                act_one_positions.append(i)

        # If we have multiple Act I markers, the last one is likely the real content
        if len(act_one_positions) > 1:
            return act_one_positions[-1]

        # Look for patterns that indicate TOC
        toc_markers = ["contents", "table of contents", "persons represented", "dramatis personae"]
        toc_start = -1

        for i, line in enumerate(lines[:200]):
            line_lower = line.lower().strip()
            for marker in toc_markers:
                if marker in line_lower:
                    toc_start = i
                    break
            if toc_start != -1:
                break

        if toc_start != -1:
            # Find where actual content starts (usually after a gap)
            consecutive_blanks = 0
            for i in range(toc_start + 1, min(len(lines), toc_start + 300)):
                if not lines[i].strip():
                    consecutive_blanks += 1
                else:
                    if consecutive_blanks > 2:
                        # Check if this looks like actual content
                        if self._is_play_element(lines[i]):
                            return i
                    consecutive_blanks = 0

        return 0

    def _parse_content(self, lines: list[str], play: Play):
        """Parse play content into acts and scenes."""
        current_act = None
        current_scene = None
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check for act marker
            if self._is_act_marker(line):
                act_info = self._parse_act_marker(line)
                if act_info:
                    # Save previous act if exists
                    if current_act and current_act.scenes:
                        play.acts.append(current_act)

                    current_act = Act(
                        number=act_info["number"], title=act_info.get("title"), scenes=[]
                    )
                    current_scene = None

            # Check for scene marker
            elif self._is_scene_marker(line):
                scene_info = self._parse_scene_marker(line)
                if scene_info:
                    # Save previous scene if exists
                    if current_scene and current_scene.elements and current_act:
                        current_act.scenes.append(current_scene)

                    current_scene = Scene(
                        number=scene_info["number"],
                        title=scene_info.get("title"),
                        location=scene_info.get("location"),
                        elements=[],
                    )

            # Check for prologue
            elif self._is_prologue_marker(line):
                i = self._parse_prologue(lines, i + 1, play)
                continue

            # Check for epilogue
            elif self._is_epilogue_marker(line):
                i = self._parse_epilogue(lines, i + 1, play)
                continue

            # Check for dramatis personae
            elif self._is_dramatis_personae(line):
                i = self._parse_dramatis_personae(lines, i + 1, play)
                continue

            # Parse scene content
            elif current_scene:
                # Check for stage direction
                if line.startswith("[") and line.endswith("]"):
                    current_scene.elements.append(
                        PlayElement(type=PlayElementType.STAGE_DIRECTION, content=line[1:-1])
                    )

                # Check for character name (all caps, often followed by period or colon)
                elif self._is_character_name(line):
                    character = self._extract_character_name(line)
                    # Look for dialogue on same or next lines
                    dialogue_lines = []

                    # Check if dialogue is on same line
                    if ":" in line or "." in line:
                        parts = line.split(":", 1) if ":" in line else line.split(".", 1)
                        if len(parts) > 1 and parts[1].strip():
                            dialogue_lines.append(parts[1].strip())

                    # Collect following lines until next element
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if not next_line:
                            break
                        if (
                            self._is_character_name(next_line)
                            or self._is_stage_direction(next_line)
                            or self._is_act_marker(next_line)
                            or self._is_scene_marker(next_line)
                        ):
                            break
                        dialogue_lines.append(next_line)
                        j += 1

                    if dialogue_lines:
                        current_scene.elements.append(
                            PlayElement(
                                type=PlayElementType.DIALOGUE,
                                content=" ".join(dialogue_lines),
                                metadata={"character": character},
                            )
                        )
                        i = j - 1  # Will be incremented at loop end

                # Regular text (description, etc.)
                else:
                    current_scene.elements.append(
                        PlayElement(type=PlayElementType.DIALOGUE, content=line)
                    )

            i += 1

        # Save final act and scene
        if current_scene and current_scene.elements and current_act:
            current_act.scenes.append(current_scene)

        if current_act and current_act.scenes:
            play.acts.append(current_act)

    def _is_play_element(self, line: str) -> bool:
        """Check if line is a play element."""
        line_upper = line.upper().strip()
        return any(
            marker in line_upper
            for marker in ["ACT ", "SCENE ", "PROLOGUE", "EPILOGUE", "ENTER ", "EXIT", "EXEUNT"]
        )

    def _is_act_marker(self, line: str) -> bool:
        """Check if line marks an act."""
        line_upper = line.upper().strip()
        # Remove trailing periods
        line_upper = line_upper.rstrip(".")
        return (
            line_upper.startswith("ACT ")
            or line_upper == "ACT"  # Sometimes just "ACT" alone
            or line_upper.startswith("ACTUS ")  # Latin
            or (line_upper.startswith("THE ") and "ACT" in line_upper)
        )

    def _parse_act_marker(self, line: str) -> Optional[dict[str, str]]:
        """Parse act marker for number and title."""
        line_stripped = line.strip().rstrip(".")

        # Extract act number (Roman or Arabic)
        words = line_stripped.split()
        for i, word in enumerate(words):
            word_clean = word.upper().strip(".,;:")
            # Roman numerals
            if all(c in "IVX" for c in word_clean) and word_clean:
                return {"number": word_clean}
            # Arabic numbers
            if word_clean.isdigit():
                return {"number": word_clean}

        # Default to Act I if no number found
        return {"number": "I"}

    def _is_scene_marker(self, line: str) -> bool:
        """Check if line marks a scene."""
        line_upper = line.upper().strip()
        return (
            line_upper.startswith("SCENE ")
            or line_upper.startswith("SC. ")
            or (line_upper.startswith("THE ") and "SCENE" in line_upper)
        )

    def _parse_scene_marker(self, line: str) -> Optional[dict[str, Any]]:
        """Parse scene marker for number, title, and location."""
        result = {}

        # Remove "SCENE" or "Scene" prefix
        line_cleaned = line
        for prefix in ["SCENE ", "Scene ", "Sc. "]:
            if line.startswith(prefix):
                line_cleaned = line[len(prefix) :].strip()
                break

        # Extract scene number (Roman or Arabic)
        parts = line_cleaned.split(".", 1)
        if len(parts) >= 1:
            first_part = parts[0].strip()
            # Check if it's a number
            if all(c in "IVXivx" for c in first_part) and first_part:
                result["number"] = first_part.upper()
                if len(parts) > 1:
                    result["location"] = parts[1].strip()
            elif first_part.isdigit():
                result["number"] = first_part
                if len(parts) > 1:
                    result["location"] = parts[1].strip()
            else:
                # No clear number, use the whole thing as location
                result["number"] = "I"  # Default
                result["location"] = line_cleaned

        return result if result else None

    def _is_character_name(self, line: str) -> bool:
        """Check if line is a character name (for dialogue)."""
        if not line or len(line) > 50:  # Character names are usually short
            return False

        # Common patterns for character names
        # 1. All caps
        # 2. Ends with period or colon
        # 3. Short line (< 30 chars)
        line_stripped = line.strip()

        # Must have at least one letter
        if not any(c.isalpha() for c in line_stripped):
            return False

        # Check if mostly uppercase letters (allowing for punctuation)
        letters = [c for c in line_stripped if c.isalpha()]
        if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.7:
            # Check if it's not a stage direction
            if not line_stripped.startswith("["):
                return True

        return False

    def _extract_character_name(self, line: str) -> str:
        """Extract character name from line."""
        # Remove trailing punctuation
        name = line.strip().rstrip(".:;")

        # If there's a colon or period, take everything before it
        for sep in [":", "."]:
            if sep in name:
                name = name.split(sep)[0]
                break

        return name.strip()

    def _is_stage_direction(self, line: str) -> bool:
        """Check if line is a stage direction."""
        line_stripped = line.strip()
        return (
            (line_stripped.startswith("[") and line_stripped.endswith("]"))
            or line_stripped.startswith("Enter ")
            or line_stripped.startswith("Exit ")
            or line_stripped.startswith("Exeunt")
        )

    def _is_prologue_marker(self, line: str) -> bool:
        """Check if line marks a prologue."""
        line_upper = line.upper().strip()
        return "PROLOGUE" in line_upper and len(line_upper) < 30

    def _parse_prologue(self, lines: list[str], start_idx: int, play: Play) -> int:
        """Parse prologue content."""
        prologue_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next major element
            if (
                self._is_act_marker(line)
                or self._is_scene_marker(line)
                or self._is_epilogue_marker(line)
            ):
                break

            if line:
                prologue_lines.append(line)

            i += 1

        play.prologue = prologue_lines
        return i

    def _is_epilogue_marker(self, line: str) -> bool:
        """Check if line marks an epilogue."""
        line_upper = line.upper().strip()
        return "EPILOGUE" in line_upper and len(line_upper) < 30

    def _parse_epilogue(self, lines: list[str], start_idx: int, play: Play) -> int:
        """Parse epilogue content."""
        epilogue_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i].strip()
            if line:
                epilogue_lines.append(line)
            i += 1

        play.epilogue = epilogue_lines
        return i

    def _is_dramatis_personae(self, line: str) -> bool:
        """Check if line marks dramatis personae."""
        line_lower = line.lower().strip()
        return (
            ("dramatis" in line_lower and "person" in line_lower)
            or line_lower == "characters"
            or line_lower == "persons represented"
        )

    def _parse_dramatis_personae(self, lines: list[str], start_idx: int, play: Play) -> int:
        """Parse character list."""
        characters = []
        i = start_idx

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next major element
            if (
                self._is_act_marker(line)
                or self._is_scene_marker(line)
                or self._is_prologue_marker(line)
            ):
                break

            # Stop at multiple blank lines
            if not line:
                blank_count = 0
                j = i
                while j < len(lines) and not lines[j].strip():
                    blank_count += 1
                    j += 1
                if blank_count > 2:
                    break
            elif line:
                characters.append(line)

            i += 1

        play.dramatis_personae = characters
        return i


def play_to_chapters(play: Play) -> list[dict[str, Any]]:
    """
    Convert Play structure to chapter format for compatibility.

    Each scene becomes a chapter.
    """
    chapters = []

    # Add prologue as first chapter if exists
    if play.prologue:
        chapters.append(
            {
                "number": 0,
                "title": "Prologue",
                "type": "prologue",
                "paragraphs": play.prologue,
                "hierarchy": [],
                "metadata": {},
            }
        )

    # Convert acts and scenes
    for act in play.acts:
        act_title = f"Act {act.number}"
        if act.title:
            act_title += f": {act.title}"

        for scene in act.scenes:
            scene_title = f"Scene {scene.number}"
            if scene.title:
                scene_title += f": {scene.title}"
            elif scene.location:
                scene_title += f": {scene.location}"

            chapters.append(
                {
                    "number": len(chapters) + 1,
                    "title": scene_title,
                    "type": "scene",
                    "paragraphs": scene.to_paragraphs(),
                    "hierarchy": [act_title],
                    "metadata": {
                        "act": act.number,
                        "scene": scene.number,
                        "location": scene.location,
                    },
                }
            )

    # Add epilogue as last chapter if exists
    if play.epilogue:
        chapters.append(
            {
                "number": len(chapters) + 1,
                "title": "Epilogue",
                "type": "epilogue",
                "paragraphs": play.epilogue,
                "hierarchy": [],
                "metadata": {},
            }
        )

    return chapters
