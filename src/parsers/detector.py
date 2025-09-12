"""
Format Detection Engine

Detects book format (standard, play, multi-part, etc.) with confidence scoring.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class BookFormat(Enum):
    """Detected book formats."""

    STANDARD = "standard"  # Regular chapters
    PLAY = "play"  # Acts and scenes
    MULTI_PART = "multi_part"  # Volumes/Books/Parts with chapters
    POETRY = "poetry"  # Collection of poems
    EPISTOLARY = "epistolary"  # Letters/diary entries
    MIXED = "mixed"  # Multiple formats
    UNKNOWN = "unknown"  # Can't determine


@dataclass
class FormatDetection:
    """Result of format detection."""

    format: BookFormat
    confidence: float  # 0-100
    evidence: Dict[str, List[str]]  # What patterns were found
    hierarchy_levels: int  # 1=flat, 2=part/chapter, 3=volume/book/chapter
    recommendations: List[str]  # Suggestions for parsing


class FormatDetector:
    """
    Detects book format using pattern matching and scoring.
    """

    def __init__(self):
        """Initialize the format detector."""
        self._setup_patterns()

        # Collection/anthology patterns
        self.collection_patterns = [
            "complete works",
            "collected works",
            "works of",
            "anthology",
            "collection",
            "complete plays",
            "complete poems",
        ]

    def _setup_patterns(self):
        """Set up detection patterns."""
        # Chapter patterns with variations
        self.chapter_patterns = [
            (r"^CHAPTER\s+[IVX]+\.?\s*$", 2.0, "CHAPTER with Roman numerals"),
            (r"^Chapter\s+[IVX]+\.?\s*$", 2.0, "Chapter with Roman numerals"),
            (r"^CHAPTER\s+\d+\.?\s*$", 2.0, "CHAPTER with numbers"),
            (r"^Chapter\s+\d+\.?\s*$", 2.0, "Chapter with numbers"),
            (r"^CHAPITRE\s+[IVX]+", 1.5, "French chapter"),
            (r"^CAPÍTULO\s+\d+", 1.5, "Spanish chapter"),
            (r"^CAPITOLO\s+[IVX]+", 1.5, "Italian chapter"),
            (r"^KAPITEL\s+\d+", 1.5, "German chapter"),
            (r"^\d+\.\s+[A-Z]", 1.0, "Numbered sections"),
            (r"^[IVX]+\.\s+[A-Z]", 1.0, "Roman numeral sections"),
        ]

        # Play patterns
        self.play_patterns = [
            (r"^ACT\s+[IVX]+\.?\s*$", 3.0, "ACT with Roman numerals"),
            (r"^Act\s+[IVX]+\.?\s*$", 3.0, "Act with Roman numerals"),
            (r"^SCENE\s+[ivxIVX]+\.?\s*$", 2.5, "SCENE marker"),
            (r"^Scene\s+[ivxIVX]+\.?\s*$", 2.5, "Scene marker"),
            (r"^\[Enter\s+[A-Z]", 2.0, "Stage direction: Enter"),
            (r"^\[Exit\s+[A-Z]", 2.0, "Stage direction: Exit"),
            (r"^\[Exeunt", 2.0, "Stage direction: Exeunt"),
            (r"Dramatis Person[aæ]", 3.0, "Character list"),
        ]

        # Multi-part patterns
        self.multipart_patterns = [
            (r"^\s*VOLUME\s+[IVX]+\.?\s*$", 3.0, "VOLUME marker"),
            (r"^\s*Volume\s+[IVX]+\.?\s*$", 3.0, "Volume marker"),
            (r"^\s*VOLUME\s+(ONE|TWO|THREE|FOUR|FIVE)", 3.0, "VOLUME spelled out"),
            (r"^\s*BOOK\s+[IVX]+\.?\s*$", 3.0, "BOOK marker"),
            (r"^\s*Book\s+[IVX]+\.?\s*$", 3.0, "Book marker"),
            (r"^\s*PART\s+[IVX]+\.?\s*$", 3.0, "PART marker"),
            (r"^\s*Part\s+[IVX]+\.?\s*$", 3.0, "Part marker"),
            (r"^\s*PART\s+(ONE|TWO|THREE|FOUR|FIVE)", 3.0, "PART spelled out"),
            (r"^TOME\s+[IVX]+", 2.0, "French volume"),
            (r"^LIBRO\s+[IVX]+", 2.0, "Spanish/Italian book"),
        ]

        # Poetry patterns
        self.poetry_patterns = [
            (r"^\d+\s*$", 1.5, "Numbered poem"),
            (r"^[IVX]+\s*$", 1.5, "Roman numeral poem"),
            (r"^Sonnet\s+\d+", 3.0, "Sonnet number"),
            (r"^ODE\s+[IVX]+", 2.5, "Ode number"),
            (r"^CANTO\s+[IVX]+", 2.5, "Canto marker"),
            (r"^\s{4,}[A-Z]", 0.5, "Indented stanza"),
        ]

        # Letter/Diary patterns
        self.epistolary_patterns = [
            (r"^Letter\s+[IVX]+", 3.0, "Letter number"),
            (r"^LETTER\s+\d+", 3.0, "LETTER number"),
            (r"^\w+day,\s+\w+\s+\d+", 2.5, "Diary date"),
            (r"^Dear\s+[A-Z]", 2.0, "Letter salutation"),
            (r"^My\s+(?:dear|dearest)\s+[A-Z]", 2.0, "Letter opening"),
            (r"^\d+\s+\w+\s+\d{4}", 2.0, "Date format"),
        ]

    def detect(self, text: str, toc: Optional[str] = None) -> FormatDetection:
        """
        Detect the format of the book.

        Args:
            text: Cleaned book text
            toc: Optional table of contents

        Returns:
            FormatDetection with format, confidence, and evidence
        """
        lines = text.split("\n")

        # Check for collection/anthology first
        first_500_lines = "\n".join(lines[:500]).lower()
        is_collection = any(pattern in first_500_lines for pattern in self.collection_patterns)

        # Sample different parts of the book
        sample_lines = self._get_sample_lines(lines)

        # Score each format
        scores = {}
        evidence = {}

        # If it's a collection, handle specially
        if is_collection:
            evidence["collection"] = ["Complete Works or Collection detected"]
            # Collections often have many plays/poems as chapters
            scores["standard"] = 50  # Treat as standard book with many chapters

        # Check standard chapter format
        scores["standard"], evidence["standard"] = self._score_patterns(
            sample_lines, self.chapter_patterns, min_matches=3
        )

        # Check play format (require strong evidence - both acts AND scenes)
        play_score, play_evidence = self._score_patterns(
            sample_lines, self.play_patterns, min_matches=5
        )
        # Only consider it a play if we find both acts and scenes
        has_acts = any("ACT" in str(e).upper() for e in play_evidence)
        has_scenes = any("SCENE" in str(e).upper() for e in play_evidence)
        if has_acts and has_scenes:
            scores["play"] = play_score
            evidence["play"] = play_evidence
        else:
            scores["play"] = play_score * 0.3  # Heavily penalize without both
            evidence["play"] = play_evidence

        # Check multi-part format
        scores["multi_part"], evidence["multi_part"] = self._score_patterns(
            sample_lines, self.multipart_patterns, min_matches=1
        )

        # Check poetry format
        scores["poetry"], evidence["poetry"] = self._score_patterns(
            sample_lines, self.poetry_patterns, min_matches=3
        )

        # Check epistolary format
        scores["epistolary"], evidence["epistolary"] = self._score_patterns(
            sample_lines, self.epistolary_patterns, min_matches=2
        )

        # Analyze TOC if available
        if toc:
            toc_format = self._analyze_toc(toc)
            if toc_format:
                scores[toc_format] = scores.get(toc_format, 0) + 20

        # Determine format and confidence
        if not scores or max(scores.values()) < 5:
            # Default to standard book format when uncertain
            # But give reasonable confidence if it's actually parsing well
            return FormatDetection(
                format=BookFormat.STANDARD,
                confidence=50,  # Medium confidence for default format
                evidence=evidence,
                hierarchy_levels=1,
                recommendations=["No strong format markers found, using standard book format"],
            )

        # Get the best format
        best_format = max(scores, key=scores.get)
        # Scale confidence more generously - if we found patterns, be confident
        raw_confidence = scores[best_format]
        if raw_confidence >= 50:
            confidence = 100  # Very strong signal
        elif raw_confidence >= 30:
            confidence = 90  # Strong signal
        elif raw_confidence >= 20:
            confidence = 75  # Good signal
        elif raw_confidence >= 10:
            confidence = 60  # Decent signal
        else:
            confidence = min(raw_confidence * 5, 50)  # Weak signal

        # Check for mixed format
        high_scores = [fmt for fmt, score in scores.items() if score > 15]
        if len(high_scores) > 1:
            # Multiple strong signals
            if "multi_part" in high_scores and "standard" in high_scores:
                # This is normal - multi-part books have chapters
                best_format = "multi_part"
                hierarchy_levels = 2
            elif "play" in high_scores and "poetry" in high_scores:
                # Shakespeare-like collections
                best_format = "mixed"
                hierarchy_levels = 2
            else:
                best_format = "mixed"
                hierarchy_levels = 1
        else:
            hierarchy_levels = self._get_hierarchy_levels(best_format, evidence)

        # Map to enum
        format_enum = {
            "standard": BookFormat.STANDARD,
            "play": BookFormat.PLAY,
            "multi_part": BookFormat.MULTI_PART,
            "poetry": BookFormat.POETRY,
            "epistolary": BookFormat.EPISTOLARY,
            "mixed": BookFormat.MIXED,
        }.get(best_format, BookFormat.UNKNOWN)

        # Generate recommendations
        recommendations = self._get_recommendations(format_enum, confidence, evidence)

        return FormatDetection(
            format=format_enum,
            confidence=confidence,
            evidence=evidence,
            hierarchy_levels=hierarchy_levels,
            recommendations=recommendations,
        )

    def _get_sample_lines(self, lines: List[str], sample_size: int = 2000) -> List[str]:
        """
        Get a representative sample of lines from the book.

        Samples from beginning, middle, and end to catch different patterns.
        """
        total_lines = len(lines)

        if total_lines <= sample_size:
            return lines

        samples = []

        # Sample from beginning (might have TOC)
        samples.extend(lines[: sample_size // 3])

        # Sample from middle
        middle_start = total_lines // 2 - sample_size // 6
        samples.extend(lines[middle_start : middle_start + sample_size // 3])

        # Sample from near end (but not the very end)
        end_start = total_lines - sample_size // 2
        samples.extend(lines[end_start : end_start + sample_size // 3])

        return samples

    def _score_patterns(
        self, lines: List[str], patterns: List[Tuple], min_matches: int = 1
    ) -> Tuple[float, List[str]]:
        """
        Score lines against patterns.

        Returns:
            Tuple of (score, list of matched evidence)
        """
        score = 0
        evidence = []
        match_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern, weight, description in patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    score += weight
                    match_count += 1
                    if len(evidence) < 10:  # Limit evidence
                        evidence.append(f"{description}: '{line[:50]}...'")

        # Require minimum matches
        if match_count < min_matches:
            score = score / 2  # Penalize sparse matches

        return score, evidence

    def _analyze_toc(self, toc: str) -> Optional[str]:
        """
        Analyze table of contents to determine format.
        """
        toc_lower = toc.lower()

        # Count different section types
        chapter_count = toc_lower.count("chapter")
        act_count = toc_lower.count("act ")
        scene_count = toc_lower.count("scene ")
        part_count = toc_lower.count("part ")
        volume_count = toc_lower.count("volume ")
        book_count = toc_lower.count("book ")
        letter_count = toc_lower.count("letter ")

        # Determine format from TOC
        if act_count > 2 or scene_count > 3:
            return "play"
        elif volume_count > 0 or (part_count > 1 and chapter_count > 3):
            return "multi_part"
        elif letter_count > 3:
            return "epistolary"
        elif chapter_count > 3:
            return "standard"

        return None

    def _get_hierarchy_levels(self, format: str, evidence: Dict) -> int:
        """
        Determine hierarchy depth from format and evidence.
        """
        if format == "multi_part":
            # Check if we have both parts/volumes AND chapters
            has_high_level = any(
                "VOLUME" in str(e) or "PART" in str(e) or "BOOK" in str(e)
                for e in evidence.get("multi_part", [])
            )
            has_chapters = bool(evidence.get("standard", []))

            if has_high_level and has_chapters:
                return 2  # Volume -> Chapter

        elif format == "play":
            # Check for acts and scenes
            has_acts = any("ACT" in str(e).upper() for e in evidence.get("play", []))
            has_scenes = any("SCENE" in str(e).upper() for e in evidence.get("play", []))

            if has_acts and has_scenes:
                return 2  # Act -> Scene

        return 1  # Flat structure

    def _get_recommendations(
        self, format: BookFormat, confidence: float, evidence: Dict
    ) -> List[str]:
        """
        Generate parsing recommendations based on detection.
        """
        recommendations = []

        if confidence < 50:
            recommendations.append("Low confidence - manual review recommended")

        if format == BookFormat.MIXED:
            recommendations.append("Multiple formats detected - may need custom parser")

        if format == BookFormat.MULTI_PART:
            recommendations.append("Use hierarchical parser for volumes/parts")

        if format == BookFormat.PLAY:
            recommendations.append("Preserve stage directions and character names")

        if format == BookFormat.POETRY:
            recommendations.append("Preserve line breaks and indentation")

        if format == BookFormat.UNKNOWN:
            recommendations.append("Format unclear - try generic paragraph parser")

        return recommendations
