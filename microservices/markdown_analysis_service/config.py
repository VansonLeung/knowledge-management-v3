"""Configuration module for Markdown Analysis Service.

Handles environment variables and service configuration with support for
hierarchical .env files (project root + service-level overrides).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_env_files() -> None:
    """Load environment variables from .env files.
    
    Priority (highest to lowest):
        1. Service-level .env (overrides all)
        2. Project root .env
        3. System environment variables
    """
    try:
        from dotenv import load_dotenv
        
        service_dir = Path(__file__).parent
        project_root = service_dir.parent.parent
        
        # Load project root .env first (lower priority)
        root_env = project_root / ".env"
        if root_env.exists():
            load_dotenv(root_env)
        
        # Load service-level .env second (higher priority, overrides)
        service_env = service_dir / ".env"
        if service_env.exists():
            load_dotenv(service_env, override=True)
            
    except ImportError:
        pass  # python-dotenv not installed


# Load environment files on module import
_load_env_files()


@dataclass(frozen=True)
class ServiceConfig:
    """Immutable service configuration."""
    
    # OpenAI API settings
    api_key: str
    base_url: str
    model: str
    
    # Analysis settings
    max_iterations: int
    max_keywords: int
    
    # Server settings
    host: str
    port: int
    
    @classmethod
    def from_env(cls) -> "ServiceConfig":
        """Create configuration from environment variables."""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_iterations=int(os.getenv("ANALYSIS_MAX_ITERATIONS", "20")),
            max_keywords=int(os.getenv("ANALYSIS_MAX_KEYWORDS", "10")),
            host=os.getenv("SERVICE_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVICE_PORT", "16009")),
        )
    
    def __str__(self) -> str:
        """Return a summary string for logging."""
        return (
            f"ServiceConfig(model={self.model}, base_url={self.base_url}, "
            f"max_iterations={self.max_iterations}, max_keywords={self.max_keywords})"
        )


# Global configuration instance
config = ServiceConfig.from_env()


def get_config() -> ServiceConfig:
    """Get the global service configuration."""
    return config


@dataclass
class AnalysisConfig:
    """Per-request analysis configuration (allows overrides)."""
    
    api_key: str
    base_url: str
    model: str
    max_keywords: int
    
    @classmethod
    def from_request(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_keywords: Optional[int] = None,
    ) -> "AnalysisConfig":
        """Create analysis config with request overrides."""
        global_config = get_config()
        return cls(
            api_key=api_key or global_config.api_key,
            base_url=base_url or global_config.base_url,
            model=model or global_config.model,
            max_keywords=max_keywords or global_config.max_keywords,
        )
