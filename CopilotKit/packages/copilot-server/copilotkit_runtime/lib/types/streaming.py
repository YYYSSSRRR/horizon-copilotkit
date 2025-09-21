"""Streaming response type definitions."""

from typing import Any, AsyncIterator, Dict, Optional
from pydantic import BaseModel


class StreamingResponse(BaseModel):
    """Streaming response type."""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True