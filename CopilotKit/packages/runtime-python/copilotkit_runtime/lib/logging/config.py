"""Logging configuration."""

from typing import Any, Callable, Optional
from pydantic import BaseModel


class LoggingConfig(BaseModel):
    """Logging configuration model."""
    enabled: bool = True
    progressive: bool = True
    level: str = "INFO"
    logger: Optional[Callable[[Any], None]] = None
    
    class Config:
        arbitrary_types_allowed = True