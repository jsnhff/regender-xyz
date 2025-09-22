"""
Simple configuration loader for the application.
"""

import json
import os
from pathlib import Path


class Config:
    """Simple configuration class."""

    def __init__(self):
        """Load configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"

        with open(config_path) as f:
            self._config = json.load(f)

    @property
    def character_chunk_size(self) -> int:
        """Tokens per chunk for character extraction."""
        return self._config.get("character_extraction", {}).get("chunk_size_tokens", 32000)

    @property
    def character_temperature(self) -> float:
        """Temperature for character extraction."""
        return self._config.get("character_extraction", {}).get("temperature", 0.3)

    @property
    def similarity_threshold(self) -> float:
        """Similarity threshold for character grouping."""
        return self._config.get("character_extraction", {}).get("similarity_threshold", 0.8)

    @property
    def transform_batch_size(self) -> int:
        """Paragraphs per batch for transformation."""
        return self._config.get("transformation", {}).get("paragraphs_per_batch", 100)

    @property
    def transform_temperature(self) -> float:
        """Temperature for transformation."""
        return self._config.get("transformation", {}).get("temperature", 0.3)

    @property
    def max_retries(self) -> int:
        """Max retries for API calls."""
        return self._config.get("transformation", {}).get("max_retries", 3)

    @property
    def target_quality(self) -> float:
        """Target quality percentage."""
        return self._config.get("quality", {}).get("target_quality", 90.0)

    @property
    def max_qc_iterations(self) -> int:
        """Max quality control iterations."""
        return self._config.get("quality", {}).get("max_iterations", 3)

    @property
    def log_level(self) -> str:
        """Logging level."""
        return self._config.get("logging", {}).get("level", "INFO")


# Global config instance
config = Config()
