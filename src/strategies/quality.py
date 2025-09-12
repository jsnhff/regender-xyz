"""
Quality Control Strategy Classes

This module defines strategies for quality control and validation.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from src.models.transformation import Transformation

from .base import Strategy


class QualityStrategy(Strategy):
    """Base class for quality control strategies."""

    @abstractmethod
    async def find_issues_async(self, transformation: Transformation) -> list[dict[str, Any]]:
        """
        Find quality issues in a transformation.

        Args:
            transformation: Transformation to check

        Returns:
            List of issues found
        """
        pass

    @abstractmethod
    async def assess_quality_async(self, transformation: Transformation) -> float:
        """
        Assess quality score of transformation.

        Args:
            transformation: Transformation to assess

        Returns:
            Quality score (0-100)
        """
        pass


class AdaptiveQualityStrategy(QualityStrategy):
    """Adaptive quality control that adjusts based on text complexity."""

    def __init__(self, target_quality: float = 90.0):
        """
        Initialize adaptive quality strategy.

        Args:
            target_quality: Target quality score
        """
        self.target_quality = target_quality

    async def execute_async(self, data: Any) -> Any:
        """Execute quality strategy."""
        if isinstance(data, Transformation):
            issues = await self.find_issues_async(data)
            score = await self.assess_quality_async(data)
            return {"issues": issues, "score": score}
        else:
            raise ValueError("QualityStrategy requires Transformation input")

    async def find_issues_async(self, transformation: Transformation) -> list[dict[str, Any]]:
        """
        Find quality issues in transformation.

        This would check for:
        - Inconsistent pronoun usage
        - Missed transformations
        - Grammatical errors
        - Context violations
        """
        issues = []

        # Check for consistency issues
        consistency_issues = await self._check_consistency(transformation)
        issues.extend(consistency_issues)

        # Check for completeness
        completeness_issues = await self._check_completeness(transformation)
        issues.extend(completeness_issues)

        # Check for grammar issues
        grammar_issues = await self._check_grammar(transformation)
        issues.extend(grammar_issues)

        return issues

    async def assess_quality_async(self, transformation: Transformation) -> float:
        """
        Assess quality score.

        Args:
            transformation: Transformation to assess

        Returns:
            Quality score (0-100)
        """
        # Start with perfect score
        score = 100.0

        # Find issues
        issues = await self.find_issues_async(transformation)

        # Deduct points for issues
        for issue in issues:
            severity = issue.get("severity", "minor")
            if severity == "critical":
                score -= 10
            elif severity == "major":
                score -= 5
            else:  # minor
                score -= 2

        # Ensure score stays in range
        return max(0, min(100, score))

    async def _check_consistency(self, transformation: Transformation) -> list[dict[str, Any]]:
        """Check for consistency issues."""
        issues = []

        # Check if character genders are consistent
        # This is a simplified check - real implementation would be more thorough
        character_usage = {}

        for change in transformation.changes:
            char = change.character_affected
            if char:
                if char not in character_usage:
                    character_usage[char] = set()
                character_usage[char].add(change.change_type)

        # Flag characters with inconsistent changes
        for char, change_types in character_usage.items():
            if len(change_types) > 3:  # Arbitrary threshold
                issues.append(
                    {
                        "type": "consistency",
                        "severity": "major",
                        "description": f"Character '{char}' has inconsistent transformations",
                        "character": char,
                    }
                )

        return issues

    async def _check_completeness(self, transformation: Transformation) -> list[dict[str, Any]]:
        """Check for completeness issues."""
        issues = []

        # Check if all characters were transformed
        expected_characters = set(c.name for c in transformation.characters_used.characters)
        transformed_characters = set(
            change.character_affected
            for change in transformation.changes
            if change.character_affected
        )

        missing = expected_characters - transformed_characters
        if missing:
            for char in missing:
                issues.append(
                    {
                        "type": "completeness",
                        "severity": "major",
                        "description": f"Character '{char}' appears to be missing transformations",
                        "character": char,
                    }
                )

        return issues

    async def _check_grammar(self, transformation: Transformation) -> list[dict[str, Any]]:
        """Check for grammar issues."""
        # Simplified - real implementation would use grammar checking
        return []


class StrictQualityStrategy(QualityStrategy):
    """Strict quality control with zero tolerance for errors."""

    async def execute_async(self, data: Any) -> Any:
        """Execute strict quality check."""
        if isinstance(data, Transformation):
            issues = await self.find_issues_async(data)
            score = await self.assess_quality_async(data)
            return {"issues": issues, "score": score}
        else:
            raise ValueError("QualityStrategy requires Transformation input")

    async def find_issues_async(self, transformation: Transformation) -> list[dict[str, Any]]:
        """Find any quality issues with strict criteria."""
        issues = []

        # Check every single change
        for i, change in enumerate(transformation.changes):
            if not change.character_affected:
                issues.append(
                    {
                        "type": "attribution",
                        "severity": "critical",
                        "description": f"Change {i} has no character attribution",
                        "change_index": i,
                    }
                )

        # Check for any unchanged text that should have been transformed
        # (This would require more sophisticated analysis in practice)

        return issues

    async def assess_quality_async(self, transformation: Transformation) -> float:
        """Strict quality assessment - any issue fails."""
        issues = await self.find_issues_async(transformation)
        return 100.0 if not issues else 0.0
