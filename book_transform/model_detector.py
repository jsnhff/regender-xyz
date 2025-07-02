"""Automatic model capability detection and configuration."""

import os
import re
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


def detect_model_from_path(model_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Detect model type and parameters from file path.
    
    Args:
        model_path: Path to the model file or directory
        
    Returns:
        Tuple of (model_type, parameters)
    """
    path_lower = model_path.lower()
    path_obj = Path(model_path)
    
    # Extract model info from path
    model_info = {
        "path": model_path,
        "name": path_obj.name,
        "size_params": None,
        "quantization": None,
        "context_window": None,
        "model_family": None
    }
    
    # Detect model family
    if "mistral" in path_lower:
        model_info["model_family"] = "mistral"
    elif "llama" in path_lower:
        model_info["model_family"] = "llama"
    elif "phi" in path_lower:
        model_info["model_family"] = "phi"
    elif "gemma" in path_lower:
        model_info["model_family"] = "gemma"
    elif "qwen" in path_lower:
        model_info["model_family"] = "qwen"
    
    # Detect model size (parameter count)
    size_patterns = [
        (r"(\d+\.?\d*)b", lambda x: float(x)),  # 7B, 13B, 70B, 3.2B
        (r"(\d+)m", lambda x: float(x) / 1000),  # 7000M -> 7B
    ]
    
    for pattern, converter in size_patterns:
        match = re.search(pattern, path_lower)
        if match:
            model_info["size_params"] = converter(match.group(1))
            break
    
    # Detect quantization
    quant_patterns = [
        r"(4bit|8bit|16bit|32bit)",
        r"(bf16|fp16|fp32)",
        r"(q4_0|q4_1|q5_0|q5_1|q8_0)",
        r"(gguf|ggml)",
    ]
    
    for pattern in quant_patterns:
        match = re.search(pattern, path_lower)
        if match:
            model_info["quantization"] = match.group(1)
            break
    
    # Detect context window size
    context_patterns = [
        (r"(\d+)k", lambda x: int(x) * 1024),  # 32k -> 32768
        (r"context-(\d+)", lambda x: int(x)),   # context-32768
    ]
    
    for pattern, converter in context_patterns:
        match = re.search(pattern, path_lower)
        if match:
            model_info["context_window"] = converter(match.group(1))
            break
    
    # Determine model type based on detected info
    model_type = _classify_model(model_info)
    
    return model_type, model_info


def _classify_model(model_info: Dict[str, Any]) -> str:
    """Classify model based on detected parameters."""
    family = model_info.get("model_family", "unknown")
    size = model_info.get("size_params", 0)
    
    # Mistral family
    if family == "mistral":
        if size <= 7:
            return "mistral-7b"
        elif size <= 24:
            return "mistral-small"
        else:
            return "mistral-medium"
    
    # Llama family
    elif family == "llama":
        if size <= 7:
            return "mistral-7b"  # Use similar config
        elif size <= 13:
            return "mistral-small"
        elif size <= 70:
            return "mistral-medium"
        else:
            return "gpt-4o"  # Large llama models are quite capable
    
    # Other families - make educated guesses
    elif family in ["phi", "gemma", "qwen"]:
        if size <= 3:
            return "mistral-7b"  # Small models
        elif size <= 7:
            return "mistral-small"
        else:
            return "mistral-medium"
    
    # Unknown - use size as guide
    else:
        if size and size <= 7:
            return "mistral-7b"
        elif size and size <= 24:
            return "mistral-small"
        else:
            return "mistral-medium"


def detect_mlx_model_capabilities() -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Detect capabilities of the MLX model from environment.
    
    Returns:
        Tuple of (model_type, capabilities)
    """
    model_path = os.getenv("MLX_MODEL_PATH")
    if not model_path:
        return None, {}
    
    model_type, model_info = detect_model_from_path(model_path)
    
    # Add MLX-specific info
    model_info["provider"] = "mlx"
    model_info["supports_streaming"] = True
    
    # Set default context window if not detected
    if not model_info.get("context_window"):
        # Common defaults by model size and family
        size = model_info.get("size_params", 7)
        family = model_info.get("model_family", "unknown")
        
        # Mistral models have evolved context windows
        if family == "mistral":
            if size <= 7:
                model_info["context_window"] = 32768  # 32k for 7B
            elif size <= 24:
                # Check version in path for Mistral Small
                if "3.2" in model_path or "2506" in model_path:
                    model_info["context_window"] = 131072  # 128k for 3.x versions
                elif "2501" in model_path:
                    model_info["context_window"] = 32768   # 32k for older versions
                else:
                    model_info["context_window"] = 131072  # Default to newer spec
            else:
                model_info["context_window"] = 131072
        else:
            # Other models
            if size <= 7:
                model_info["context_window"] = 8192
            elif size <= 24:
                model_info["context_window"] = 32768
            else:
                model_info["context_window"] = 65536
    
    return model_type, model_info


def auto_detect_model(provider: Optional[str] = None, 
                     model_name: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Auto-detect model type and capabilities.
    
    Args:
        provider: The LLM provider (openai, grok, mlx)
        model_name: Optional model name override
        
    Returns:
        Tuple of (model_type, capabilities)
    """
    # If model name provided, try to match it
    if model_name:
        # Direct return if it's a known model
        from .model_capabilities import MODEL_CAPABILITIES
        if model_name in MODEL_CAPABILITIES:
            return model_name, {"explicit": True}
        
        # Try pattern matching
        from .model_capabilities import MODEL_PATTERNS
        model_lower = model_name.lower()
        for pattern, capability_key in MODEL_PATTERNS.items():
            if re.search(pattern, model_lower, re.IGNORECASE):
                return capability_key, {"matched_pattern": pattern}
    
    # Provider-specific detection
    if provider == "mlx":
        model_type, info = detect_mlx_model_capabilities()
        if model_type:
            return model_type, info
    
    # Default fallbacks by provider
    defaults = {
        "openai": ("gpt-4o-mini", {"provider_default": True}),
        "grok": ("grok-beta", {"provider_default": True}),
        "mlx": ("mistral-7b", {"provider_default": True})
    }
    
    if provider and provider in defaults:
        return defaults[provider]
    
    # Ultimate fallback
    return "mistral-7b", {"fallback": True}


def get_model_display_name(model_path: Optional[str] = None, 
                          provider: Optional[str] = None) -> str:
    """Get a human-readable model name for display."""
    if provider == "mlx" and model_path:
        path_obj = Path(model_path)
        # Clean up the name
        name = path_obj.name
        name = name.replace("-", " ").replace("_", " ")
        # Capitalize appropriately
        parts = name.split()
        formatted_parts = []
        for part in parts:
            if part.lower() in ["mlx", "gguf", "ggml", "bf16", "fp16"]:
                formatted_parts.append(part.upper())
            elif re.match(r"\d+[bBmM]", part):
                formatted_parts.append(part.upper())
            else:
                formatted_parts.append(part.capitalize())
        return " ".join(formatted_parts)
    
    return model_path or "Unknown Model"