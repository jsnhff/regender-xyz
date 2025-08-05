"""Model configuration loader for verified model specifications."""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Import existing classes
from .model_capabilities import ModelTier, PromptComplexity


@dataclass
class VerifiedModelConfig:
    """Verified model configuration with metadata."""
    # Core capabilities
    provider: str | List[str]
    tier: ModelTier
    context_window: int
    output_limit: Optional[int]  # None if unverified
    
    # Feature support
    supports_json_mode: bool = False
    supports_system_messages: bool = True
    supports_function_calling: bool = False
    requires_json_in_prompt: bool = True
    
    # Chunking configuration
    chunking: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    verified: bool = True
    verification_date: Optional[str] = None
    notes: Optional[str] = None
    
    # Optional fields
    model_family: Optional[str] = None
    parameter_count: Optional[float] = None
    version_specific: Optional[Dict[str, Dict[str, Any]]] = None
    mlx_memory_config: Optional[Dict[str, Any]] = None
    
    def get_chunking_config(self) -> Dict[str, int]:
        """Get chunking configuration with defaults."""
        defaults = {
            "sentences_per_chunk": 50,
            "max_chunk_tokens": 4000
        }
        return {**defaults, **self.chunking}


class ModelConfigLoader:
    """Loads and manages verified model configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader."""
        if config_path is None:
            # Look for config file relative to this module
            module_dir = Path(__file__).parent.parent
            config_path = module_dir / "config" / "models.json"
        
        self.config_path = Path(config_path)
        self._config_data: Optional[Dict[str, Any]] = None
        self._models: Dict[str, VerifiedModelConfig] = {}
        self._patterns: Dict[str, List[str]] = {}
        
        # Load configuration
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config_data = json.load(f)
        
        # Parse verified models
        for model_id, model_data in self._config_data.get("models", {}).items():
            self._models[model_id] = self._parse_model_config(model_data)
        
        # Parse pattern matching
        pattern_data = self._config_data.get("pattern_matching", {}).get("patterns", {})
        for model_id, patterns in pattern_data.items():
            if isinstance(patterns, list):
                self._patterns[model_id] = patterns
            else:
                self._patterns[model_id] = [patterns]
    
    def _parse_model_config(self, data: Dict[str, Any]) -> VerifiedModelConfig:
        """Parse model configuration data."""
        # Map tier string to enum
        tier_str = data.get("tier", "basic")
        tier_map = {
            "basic": ModelTier.BASIC,
            "standard": ModelTier.STANDARD,
            "advanced": ModelTier.ADVANCED,
            "flagship": ModelTier.FLAGSHIP
        }
        tier = tier_map.get(tier_str, ModelTier.BASIC)
        
        return VerifiedModelConfig(
            provider=data["provider"],
            tier=tier,
            context_window=data["context_window"],
            output_limit=data.get("output_limit"),
            supports_json_mode=data.get("supports_json_mode", False),
            supports_system_messages=data.get("supports_system_messages", True),
            supports_function_calling=data.get("supports_function_calling", False),
            requires_json_in_prompt=data.get("requires_json_in_prompt", True),
            chunking=data.get("chunking", {}),
            verified=data.get("verified", True),
            verification_date=data.get("verification_date"),
            notes=data.get("notes"),
            model_family=data.get("model_family"),
            parameter_count=data.get("parameter_count"),
            version_specific=data.get("version_specific"),
            mlx_memory_config=data.get("mlx_memory_config")
        )
    
    def get_model_config(self, model_name: Optional[str] = None, 
                        provider: Optional[str] = None,
                        model_path: Optional[str] = None) -> Optional[VerifiedModelConfig]:
        """Get configuration for a model."""
        
        # Direct lookup
        if model_name and model_name in self._models:
            return self._models[model_name]
        
        # Pattern matching
        if model_name:
            model_lower = model_name.lower()
            
            # Check each pattern
            for model_id, patterns in self._patterns.items():
                for pattern in patterns:
                    if re.search(pattern, model_lower, re.IGNORECASE):
                        return self._models.get(model_id)
        
        # Version-specific lookup for model paths
        if model_path:
            path_lower = model_path.lower()
            
            # Check for version-specific configs
            for model_id, config in self._models.items():
                if config.version_specific:
                    for version, version_data in config.version_specific.items():
                        if version in path_lower:
                            # Create a modified config with version-specific overrides
                            modified_config = VerifiedModelConfig(
                                provider=config.provider,
                                tier=config.tier,
                                context_window=version_data.get("context_window", config.context_window),
                                output_limit=version_data.get("output_limit", config.output_limit),
                                supports_json_mode=config.supports_json_mode,
                                supports_system_messages=config.supports_system_messages,
                                supports_function_calling=config.supports_function_calling,
                                requires_json_in_prompt=config.requires_json_in_prompt,
                                chunking=config.chunking,
                                verified=config.verified,
                                verification_date=config.verification_date,
                                notes=f"{config.notes} (Version: {version})" if config.notes else f"Version: {version}",
                                model_family=config.model_family,
                                parameter_count=config.parameter_count,
                                mlx_memory_config=config.mlx_memory_config
                            )
                            return modified_config
        
        # Provider defaults
        if provider:
            provider_defaults = self._config_data.get("provider_defaults", {})
            default_model = provider_defaults.get(provider)
            if default_model and default_model in self._models:
                return self._models[default_model]
        
        return None
    
    def list_verified_models(self) -> List[str]:
        """List all verified model IDs."""
        return list(self._models.keys())
    
    def get_provider_models(self, provider: str) -> List[str]:
        """Get all models for a specific provider."""
        models = []
        for model_id, config in self._models.items():
            if isinstance(config.provider, list):
                if provider in config.provider:
                    models.append(model_id)
            elif config.provider == provider:
                models.append(model_id)
        return models
    
    def get_tier_info(self, tier: ModelTier) -> Dict[str, Any]:
        """Get information about a tier."""
        tier_data = self._config_data.get("tiers", {}).get(tier.value, {})
        return tier_data
    
    def is_model_verified(self, model_name: str) -> bool:
        """Check if a model has verified specifications."""
        config = self.get_model_config(model_name)
        return config is not None and config.verified


# Global instance
_config_loader: Optional[ModelConfigLoader] = None


def get_config_loader() -> ModelConfigLoader:
    """Get or create the global config loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ModelConfigLoader()
    return _config_loader


def get_verified_model_config(model_name: Optional[str] = None,
                            provider: Optional[str] = None,
                            model_path: Optional[str] = None) -> Optional[VerifiedModelConfig]:
    """Get verified model configuration."""
    loader = get_config_loader()
    return loader.get_model_config(model_name, provider, model_path)


def get_model_context_window(model_name: Optional[str] = None,
                           provider: Optional[str] = None,
                           model_path: Optional[str] = None) -> int:
    """Get the context window for a model."""
    config = get_verified_model_config(model_name, provider, model_path)
    if config:
        return config.context_window
    
    # Fallback to conservative default
    return 8192


def get_model_output_limit(model_name: Optional[str] = None,
                         provider: Optional[str] = None,
                         model_path: Optional[str] = None) -> Optional[int]:
    """Get the output token limit for a model."""
    config = get_verified_model_config(model_name, provider, model_path)
    if config:
        return config.output_limit
    
    # Return None if unknown
    return None