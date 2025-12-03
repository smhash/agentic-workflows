"""Model configuration for multi-agent research workflow."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# Valid OpenAI model patterns
VALID_MODEL_PATTERNS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "o1",
    "o1-mini",
    "o1-preview",
    "o1-2024-",
]


def validate_model_name(model: str) -> None:
    """
    Validate that a model name is a recognized OpenAI model.
    
    Args:
        model: The model name to validate.
        
    Raises:
        ValueError: If the model name is not recognized.
    """
    # Check if it matches any known pattern
    is_valid = any(
        model.startswith(pattern.rstrip("*")) or pattern.rstrip("*") in model
        for pattern in VALID_MODEL_PATTERNS
    )
    
    # Also allow custom models that look like OpenAI models
    if not is_valid:
        # Check if it looks like a valid OpenAI model format
        valid_prefixes = ["gpt-", "o1"]
        if not any(model.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Invalid model name: '{model}'. "
                f"Expected an OpenAI model (e.g., gpt-4o, gpt-4o-mini, o1-mini). "
                f"Valid patterns: {', '.join(VALID_MODEL_PATTERNS)}"
            )


@dataclass
class ModelConfig:
    """
    Configuration for model selection across agents in the research workflow.
    
    Each agent type can use a different model optimized for its specific task:
    - planner: Simple structured output (default: gpt-4o-mini)
    - router: Simple classification/routing (default: gpt-4o-mini)
    - research: Complex reasoning with tool use (default: gpt-4o)
    - writer: Quality writing and content generation (default: gpt-4o)
    - editor: Critical analysis and revision (default: gpt-4o)
    """
    
    planner: str = "gpt-4o-mini"  # Changed from o1-preview as o1 models may not be available to all users
    router: str = "gpt-4o-mini"
    research: str = "gpt-4o"
    writer: str = "gpt-4o"
    editor: str = "gpt-4o"
    
    def __post_init__(self) -> None:
        """Validate all model names after initialization."""
        validate_model_name(self.planner)
        validate_model_name(self.router)
        validate_model_name(self.research)
        validate_model_name(self.writer)
        validate_model_name(self.editor)
    
    @classmethod
    def default(cls) -> "ModelConfig":
        """
        Return default model configuration optimized for production use.
        
        Returns:
            ModelConfig: Default configuration with cost-optimized model selection.
        """
        return cls()
    
    @classmethod
    def for_testing(cls) -> "ModelConfig":
        """
        Return model configuration optimized for testing (uses cheaper models).
        
        Returns:
            ModelConfig: Testing configuration with all models set to gpt-4o-mini.
        """
        return cls(
            planner="gpt-4o-mini",
            router="gpt-4o-mini",
            research="gpt-4o-mini",
            writer="gpt-4o-mini",
            editor="gpt-4o-mini"
        )
    
    @classmethod
    def from_env(cls) -> "ModelConfig":
        """
        Create ModelConfig from environment variables.
        
        Environment variables:
            PLANNER_MODEL: Model for planner agent (default: gpt-4o-mini)
            ROUTER_MODEL: Model for router agent (default: gpt-4o-mini)
            RESEARCH_MODEL: Model for research agent (default: gpt-4o)
            WRITER_MODEL: Model for writer agent (default: gpt-4o)
            EDITOR_MODEL: Model for editor agent (default: gpt-4o)
        
        Returns:
            ModelConfig: Configuration loaded from environment variables.
        """
        return cls(
            planner=os.getenv("PLANNER_MODEL", "gpt-4o-mini"),
            router=os.getenv("ROUTER_MODEL", "gpt-4o-mini"),
            research=os.getenv("RESEARCH_MODEL", "gpt-4o"),
            writer=os.getenv("WRITER_MODEL", "gpt-4o"),
            editor=os.getenv("EDITOR_MODEL", "gpt-4o")
        )

