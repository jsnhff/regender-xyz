"""Model capability tiers and configurations for generic model handling."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ModelTier(Enum):
    """Model capability tiers."""
    BASIC = "basic"           # Simple instructions, limited context
    STANDARD = "standard"     # Good instruction following, moderate context
    ADVANCED = "advanced"     # Complex reasoning, large context
    FLAGSHIP = "flagship"     # Best capabilities, huge context


class PromptComplexity(Enum):
    """Prompt complexity levels."""
    SIMPLE = "simple"         # Basic instructions only
    MODERATE = "moderate"     # Some structure, clear formatting
    COMPLEX = "complex"       # Detailed instructions, exact requirements
    ADVANCED = "advanced"     # Complex JSON schemas, position tracking


@dataclass
class ModelCapabilities:
    """Defines capabilities for a model or model family."""
    tier: ModelTier
    context_window: int
    output_limit: int
    supports_json_mode: bool = False
    supports_system_messages: bool = True
    supports_function_calling: bool = False
    max_prompt_complexity: PromptComplexity = PromptComplexity.MODERATE
    requires_json_in_prompt: bool = True
    chunking_config: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default chunking config based on tier if not provided."""
        if not self.chunking_config:
            tier_defaults = {
                ModelTier.BASIC: {"sentences_per_chunk": 30, "max_chunk_tokens": 2000},
                ModelTier.STANDARD: {"sentences_per_chunk": 50, "max_chunk_tokens": 4000},
                ModelTier.ADVANCED: {"sentences_per_chunk": 75, "max_chunk_tokens": 5000},
                ModelTier.FLAGSHIP: {"sentences_per_chunk": 100, "max_chunk_tokens": 6000},
            }
            self.chunking_config = tier_defaults.get(self.tier, tier_defaults[ModelTier.STANDARD])


# Model capability registry
MODEL_CAPABILITIES = {
    # OpenAI Models
    "gpt-4": ModelCapabilities(
        tier=ModelTier.ADVANCED,
        context_window=8192,
        output_limit=4096,
        supports_json_mode=True,
        max_prompt_complexity=PromptComplexity.COMPLEX,
        requires_json_in_prompt=False
    ),
    "gpt-4o": ModelCapabilities(
        tier=ModelTier.FLAGSHIP,
        context_window=128000,
        output_limit=4096,
        supports_json_mode=True,
        max_prompt_complexity=PromptComplexity.ADVANCED,
        requires_json_in_prompt=False
    ),
    "gpt-4o-mini": ModelCapabilities(
        tier=ModelTier.STANDARD,
        context_window=128000,
        output_limit=4096,
        supports_json_mode=True,
        max_prompt_complexity=PromptComplexity.COMPLEX,
        requires_json_in_prompt=False
    ),
    
    # Grok Models
    "grok-beta": ModelCapabilities(
        tier=ModelTier.ADVANCED,
        context_window=131072,
        output_limit=8192,
        supports_json_mode=False,  # Requires JSON instructions in prompt
        max_prompt_complexity=PromptComplexity.COMPLEX
    ),
    "grok-3-mini-fast": ModelCapabilities(
        tier=ModelTier.STANDARD,
        context_window=32768,
        output_limit=4096,
        supports_json_mode=False,
        max_prompt_complexity=PromptComplexity.MODERATE,
        chunking_config={"sentences_per_chunk": 30, "max_chunk_tokens": 2500}
    ),
    
    # Mistral Models (via MLX or API)
    "mistral-7b": ModelCapabilities(
        tier=ModelTier.BASIC,
        context_window=32768,
        output_limit=2048,
        supports_json_mode=False,
        max_prompt_complexity=PromptComplexity.SIMPLE
    ),
    "mistral-small": ModelCapabilities(
        tier=ModelTier.STANDARD,
        context_window=131072,  # 128k context window for 3.x versions
        output_limit=2048,
        supports_json_mode=False,
        max_prompt_complexity=PromptComplexity.MODERATE
    ),
    "mistral-medium": ModelCapabilities(
        tier=ModelTier.ADVANCED,
        context_window=32768,
        output_limit=2048,
        supports_json_mode=False,
        max_prompt_complexity=PromptComplexity.COMPLEX
    ),
}

# Pattern-based model matching for flexibility
MODEL_PATTERNS = {
    # OpenAI patterns
    r"gpt-4o-mini": "gpt-4o-mini",
    r"gpt-4o": "gpt-4o",
    r"gpt-4": "gpt-4",
    
    # Grok patterns
    r"grok-beta": "grok-beta",
    r"grok-.*mini.*fast": "grok-3-mini-fast",
    
    # Mistral patterns
    r"mistral.*small.*24[bB]": "mistral-small",
    r"mistral.*medium": "mistral-medium",
    r"mistral.*7[bB]": "mistral-7b",
    
    # Llama patterns (future)
    r"llama.*7[bB]": "mistral-7b",  # Use similar config as mistral-7b
    r"llama.*13[bB]": "mistral-small",
    r"llama.*70[bB]": "mistral-medium",
}


def get_model_capabilities(model_name: Optional[str] = None, 
                         provider: Optional[str] = None) -> ModelCapabilities:
    """Get capabilities for a model, with pattern matching and fallbacks."""
    
    # Direct lookup
    if model_name and model_name in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[model_name]
    
    # Pattern matching
    if model_name:
        import re
        model_lower = model_name.lower()
        for pattern, capability_key in MODEL_PATTERNS.items():
            if re.search(pattern, model_lower, re.IGNORECASE):
                return MODEL_CAPABILITIES[capability_key]
    
    # Provider-based defaults
    provider_defaults = {
        "openai": MODEL_CAPABILITIES["gpt-4o-mini"],
        "grok": MODEL_CAPABILITIES["grok-beta"],
        "mlx": MODEL_CAPABILITIES["mistral-7b"],
    }
    
    if provider and provider in provider_defaults:
        return provider_defaults[provider]
    
    # Ultimate fallback - basic tier
    return ModelCapabilities(
        tier=ModelTier.BASIC,
        context_window=8192,
        output_limit=2048,
        supports_json_mode=False,
        max_prompt_complexity=PromptComplexity.SIMPLE
    )


def supports_complex_prompts(model_name: Optional[str] = None, 
                           provider: Optional[str] = None) -> bool:
    """Check if a model supports complex prompts."""
    caps = get_model_capabilities(model_name, provider)
    return caps.max_prompt_complexity in [PromptComplexity.COMPLEX, PromptComplexity.ADVANCED]


def supports_json_mode(model_name: Optional[str] = None, 
                      provider: Optional[str] = None) -> bool:
    """Check if a model supports JSON mode."""
    caps = get_model_capabilities(model_name, provider)
    return caps.supports_json_mode


def get_optimal_chunk_config(model_name: Optional[str] = None, 
                           provider: Optional[str] = None) -> Dict[str, int]:
    """Get optimal chunking configuration for a model."""
    caps = get_model_capabilities(model_name, provider)
    return caps.chunking_config