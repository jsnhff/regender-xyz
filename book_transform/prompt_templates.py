"""Adaptive prompt templates based on model capabilities."""

from typing import Dict, Any, Optional
from .model_capabilities import (
    ModelCapabilities, PromptComplexity, ModelTier,
    get_model_capabilities
)


class PromptTemplate:
    """Base class for adaptive prompt templates."""
    
    def __init__(self, model_name: Optional[str] = None, 
                 provider: Optional[str] = None):
        self.capabilities = get_model_capabilities(model_name, provider)
    
    def format(self, **kwargs) -> Dict[str, str]:
        """Format the prompt based on model capabilities."""
        raise NotImplementedError


class TransformationPrompt(PromptTemplate):
    """Adaptive transformation prompt."""
    
    def format(self, text: str, transform_type: str, 
               character_context: Optional[str] = None, **kwargs) -> Dict[str, str]:
        """Generate transformation prompt based on model capabilities."""
        
        # Get transformation details
        from .llm_transform import TRANSFORM_TYPES
        transform_info = TRANSFORM_TYPES[transform_type]
        
        # Build base prompt components
        if self.capabilities.max_prompt_complexity == PromptComplexity.SIMPLE:
            return self._simple_transform_prompt(text, transform_info, character_context)
        elif self.capabilities.max_prompt_complexity == PromptComplexity.MODERATE:
            return self._moderate_transform_prompt(text, transform_info, character_context)
        else:  # COMPLEX or ADVANCED
            return self._complex_transform_prompt(text, transform_info, character_context)
    
    def _simple_transform_prompt(self, text: str, transform_info: Dict, 
                                character_context: Optional[str]) -> Dict[str, str]:
        """Simple transformation prompt."""
        system = f"You transform text to use {transform_info['name'].lower()} gender forms."
        
        changes = '\n'.join(f"- {change}" for change in transform_info['changes'][:3])
        
        user = f"""Change gender references to {transform_info['name'].lower()}.

Changes:
{changes}

{f"Characters: {character_context}" if character_context else ""}

Text:
{text}

Output the transformed text only."""

        return {"system": system, "user": user}
    
    def _moderate_transform_prompt(self, text: str, transform_info: Dict,
                                  character_context: Optional[str]) -> Dict[str, str]:
        """Moderate complexity transformation."""
        system = f"""You are a text transformation assistant specializing in gender representation.
Transform text to use {transform_info['name'].lower()} forms while preserving meaning."""
        
        changes = '\n'.join(f"- {change}" for change in transform_info['changes'])
        
        output_format = self._get_output_format()
        char_info = f"Character information:\n{character_context}\n" if character_context else ""
        
        user = f"""Transform this text to use {transform_info['name'].lower()} gender representation.

Required changes:
{changes}

Rules:
1. Transform ALL gender references consistently
2. Keep the original meaning and style
3. Preserve all formatting and punctuation
4. Make changes sound natural

{char_info}

Text to transform:
{text}

{output_format}"""

        return {"system": system, "user": user}
    
    def _complex_transform_prompt(self, text: str, transform_info: Dict,
                                 character_context: Optional[str]) -> Dict[str, str]:
        """Complex transformation with detailed instructions."""
        output_format = self._get_output_format()
        
        system = """You are an advanced literary transformation system.
Your task is to precisely transform gender representation while maintaining narrative integrity.
You must preserve all stylistic elements and ensure consistency."""
        
        changes = '\n'.join(f"  - {change}" for change in transform_info['changes'])
        
        user = f"""Execute gender transformation: {transform_info['description']}

TRANSFORMATION RULES:
{changes}

CRITICAL REQUIREMENTS:
1. Transform ALL gendered language consistently
2. Maintain exact punctuation, capitalization, and formatting
3. Preserve narrative voice, tone, and style
4. Ensure grammatical correctness after changes
5. Apply transformations uniformly to all character references
6. Handle context-dependent words appropriately

{f"CHARACTER CONTEXT:{chr(10)}{character_context}{chr(10)}" if character_context else ""}

QUALITY CHECKS:
- Consistency: Same character = same gender throughout
- Naturalness: Changes must read naturally
- Completeness: No gendered terms left unchanged
- Accuracy: Preserve all non-gender elements exactly

TEXT FOR TRANSFORMATION:
{text}

{output_format}"""

        return {"system": system, "user": user}
    
    def _get_output_format(self) -> str:
        """Get output format instructions based on capabilities."""
        if self.capabilities.supports_json_mode and not self.capabilities.requires_json_in_prompt:
            # Model handles JSON natively
            return ""
        elif self.capabilities.tier in [ModelTier.STANDARD, ModelTier.ADVANCED, ModelTier.FLAGSHIP]:
            # Can handle JSON with instructions
            return """
OUTPUT FORMAT (JSON):
{
    "transformed_text": "the complete transformed text",
    "changes_made": ["list of specific changes"],
    "characters_affected": ["character names affected"]
}

Ensure proper JSON escaping for quotes."""
        else:
            # Basic models - text only
            return "\nOutput only the transformed text, no explanations or JSON."


def get_prompt(prompt_type: str, model_name: Optional[str] = None,
               provider: Optional[str] = None, **kwargs) -> Dict[str, str]:
    """Get an appropriate prompt for the model and task."""
    
    prompt_classes = {
        "transformation": TransformationPrompt,
    }
    
    if prompt_type not in prompt_classes:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    prompt_class = prompt_classes[prompt_type]
    prompt = prompt_class(model_name, provider)
    
    return prompt.format(**kwargs)