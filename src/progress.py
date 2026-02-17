"""
Progress Reporting Module

This module provides event types and context for progress reporting
during book processing operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol


class Stage(Enum):
    """Processing stages."""

    PARSING = "parsing"
    ANALYZING = "analyzing"
    TRANSFORMING = "transforming"
    QUALITY_CONTROL = "qc"


@dataclass
class CharacterPreview:
    """Preview of a character transformation."""

    name: str
    original_gender: str
    new_gender: str
    new_name: Optional[str] = None

    def __str__(self) -> str:
        if self.new_name and self.new_name != self.name:
            return f"{self.name} ({self.original_gender}) -> {self.new_name} ({self.new_gender})"
        return f"{self.name} ({self.original_gender}) -> ({self.new_gender})"


@dataclass
class ProgressEvent:
    """Event for progress updates."""

    stage: Stage
    current: int
    total: int
    message: Optional[str] = None


@dataclass
class StageCompleteEvent:
    """Event when a stage completes."""

    stage: Stage
    elapsed_seconds: float
    stats: dict[str, Any] = field(default_factory=dict)
    characters: list[CharacterPreview] = field(default_factory=list)


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    def on_progress(self, event: ProgressEvent) -> None:
        """Called when progress updates."""
        ...

    def on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Called when a stage completes."""
        ...


class ProgressContext:
    """
    Context for reporting progress during processing.

    This class allows services to report progress without being
    tightly coupled to a specific display implementation.
    """

    def __init__(
        self,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
        on_stage_complete: Optional[Callable[[StageCompleteEvent], None]] = None,
    ):
        """
        Initialize progress context.

        Args:
            on_progress: Callback for progress updates
            on_stage_complete: Callback for stage completion
        """
        self._on_progress = on_progress
        self._on_stage_complete = on_stage_complete

    def report_progress(
        self,
        stage: Stage,
        current: int,
        total: int,
        message: Optional[str] = None,
    ) -> None:
        """
        Report progress update.

        Args:
            stage: Current processing stage
            current: Current item number
            total: Total items
            message: Optional status message
        """
        if self._on_progress:
            event = ProgressEvent(
                stage=stage,
                current=current,
                total=total,
                message=message,
            )
            self._on_progress(event)

    def report_stage_complete(
        self,
        stage: Stage,
        elapsed_seconds: float,
        stats: Optional[dict[str, Any]] = None,
        characters: Optional[list[CharacterPreview]] = None,
    ) -> None:
        """
        Report stage completion.

        Args:
            stage: Completed stage
            elapsed_seconds: Time taken
            stats: Stage statistics
            characters: Character previews (for analysis stage)
        """
        if self._on_stage_complete:
            event = StageCompleteEvent(
                stage=stage,
                elapsed_seconds=elapsed_seconds,
                stats=stats or {},
                characters=characters or [],
            )
            self._on_stage_complete(event)
