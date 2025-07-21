"""Agent type definitions."""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class AgentState(BaseModel):
    """Agent state type."""
    agent_name: str
    state: Dict[str, Any]
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    active: bool = False
    running: bool = False