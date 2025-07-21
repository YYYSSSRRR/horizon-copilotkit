"""Message type definitions."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class Role(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"
    TOOL = "tool"
    DEVELOPER = "developer"


class Message(BaseModel):
    """Universal message type with all capabilities."""
    id: str
    role: str = "user"
    content: Any = ""
    
    # Text message fields
    text_content: Optional[str] = None
    
    # Image message fields
    format: Optional[str] = None
    bytes: Optional[str] = None
    
    # Action execution fields
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    
    # Result message fields
    result: Optional[str] = None
    action_execution_id: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_text_message(self) -> bool:
        """Check if this is a text message."""
        return self.role in ["user", "assistant", "system", "developer"] and not self.name
    
    def is_image_message(self) -> bool:
        """Check if this is an image message."""
        return self.format is not None and self.bytes is not None
    
    def is_action_execution_message(self) -> bool:
        """Check if this is an action execution message."""
        return self.role == "assistant" and self.name is not None
    
    def is_result_message(self) -> bool:
        """Check if this is a result message."""
        return self.role == "tool" or (self.result is not None and self.action_execution_id is not None)


class BaseMessage(BaseModel):
    """Base message type."""
    id: str
    role: Role
    content: Any


class TextMessage(BaseMessage):
    """Text message type."""
    content: str


class FunctionMessage(BaseMessage):
    """Function message type."""
    role: Role = Role.FUNCTION
    name: str
    content: Any