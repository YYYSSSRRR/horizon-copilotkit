"""Action type definitions."""

from typing import Any, Dict, Optional, List, Callable, Awaitable
from pydantic import BaseModel


class Parameter(BaseModel):
    """Action parameter definition."""
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False


class Action(BaseModel):
    """Action definition."""
    name: str
    description: Optional[str] = None
    parameters: Optional[List[Parameter]] = None
    handler: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None
    
    class Config:
        arbitrary_types_allowed = True
        
    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute the action with given arguments."""
        if self.handler:
            return await self.handler(arguments)
        else:
            raise NotImplementedError(f"No handler defined for action: {self.name}")


class ActionInput(BaseModel):
    """Action input type."""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    json_schema: Optional[str] = None


class ActionResult(BaseModel):
    """Action result type."""
    action_name: str
    result: Any
    success: bool = True
    error: Optional[str] = None