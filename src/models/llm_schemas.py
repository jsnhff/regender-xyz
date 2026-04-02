"""
Pydantic schemas for LLM responses.

These schemas enforce structure and validation for LLM responses,
ensuring consistent JSON parsing across different providers.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CharacterExtraction(BaseModel):
    """Schema for a single character extraction."""

    name: str = Field(..., description="Character's primary name")
    gender: str = Field(default="unknown", description="male/female/unknown/neutral")
    pronouns: str = Field(default="", description="Pronouns used for the character")
    description: str = Field(default="", description="Brief character description")
    aliases: list[str] = Field(default_factory=list, description="Alternate names/titles")
    titles: list[str] = Field(default_factory=list, description="Titles (Dr., Captain, etc.)")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Normalize gender values."""
        v = v.lower().strip()
        if v in ["m", "man", "boy", "male"]:
            return "male"
        elif v in ["f", "woman", "girl", "female"]:
            return "female"
        elif v in ["neutral", "non-binary", "nonbinary", "nb"]:
            return "neutral"
        elif v in ["unknown", "unclear", ""]:
            return "unknown"
        return v

    @field_validator("aliases", "titles")
    @classmethod
    def clean_list(cls, v: list[str]) -> list[str]:
        """Clean and deduplicate list values."""
        if not v:
            return []
        # Remove empty strings and duplicates
        return list(dict.fromkeys(s.strip() for s in v if s.strip()))


class CharacterExtractionResponse(BaseModel):
    """Schema for character extraction response from LLM."""

    characters: list[CharacterExtraction] = Field(
        default_factory=list, description="List of extracted characters"
    )

    def to_dict_list(self) -> list[dict]:
        """Convert to list of dictionaries for compatibility."""
        return [char.model_dump() for char in self.characters]


class CharacterMergeResponse(BaseModel):
    """Schema for character merge/deduplication response."""

    is_same_person: bool = Field(..., description="Whether characters are the same person")
    canonical_name: str = Field(..., description="Primary name to use")
    gender: str = Field(default="unknown", description="Combined gender assessment")
    pronouns: str = Field(default="", description="Combined pronouns")
    description: str = Field(default="", description="Combined description")
    aliases: list[str] = Field(default_factory=list, description="All alternate names")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Normalize gender values."""
        v = v.lower().strip()
        if v in ["m", "man", "boy", "male"]:
            return "male"
        elif v in ["f", "woman", "girl", "female"]:
            return "female"
        elif v in ["neutral", "non-binary", "nonbinary", "nb"]:
            return "neutral"
        elif v in ["unknown", "unclear", ""]:
            return "unknown"
        return v

    @field_validator("aliases")
    @classmethod
    def clean_aliases(cls, v: list[str]) -> list[str]:
        """Clean and deduplicate aliases."""
        if not v:
            return []
        return list(dict.fromkeys(s.strip() for s in v if s.strip()))


class CharacterGroupAnalysis(BaseModel):
    """Schema for analyzing a group of characters for potential merging."""

    characters: list[CharacterExtraction] = Field(..., description="Characters to analyze")
    merge_groups: list[list[int]] = Field(
        default_factory=list, description="Indices of characters that should be merged"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in grouping")


class ValidationError(BaseModel):
    """Schema for validation error responses."""

    error: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the error")
