"""Model Context Protocol (MCP) integration."""

from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel

from .types.actions import Action


class MCPEndpointConfig(BaseModel):
    """MCP endpoint configuration."""
    endpoint: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    description: str
    schema: Dict[str, Any]
    execute: Any  # Callable
    
    class Config:
        arbitrary_types_allowed = True


class MCPClient(Protocol):
    """Protocol for MCP client."""
    
    async def tools(self) -> List[MCPTool]:
        """Get available tools from MCP server."""
        ...


def convert_mcp_tools_to_actions(tools: List[MCPTool], endpoint_url: str) -> List[Action]:
    """Convert MCP tools to CopilotKit actions."""
    actions = []
    
    for tool in tools:
        # Create action from MCP tool
        action = Action(
            name=tool.description.split(':')[0].strip() if ':' in tool.description else tool.description,
            description=tool.description,
            parameters=[],  # Would extract from schema
            handler=tool.execute
        )
        # Mark as MCP tool
        setattr(action, '_is_mcp_tool', True)
        setattr(action, '_mcp_endpoint', endpoint_url)
        actions.append(action)
    
    return actions


def generate_mcp_tool_instructions(tools_map: Dict[str, MCPTool]) -> str:
    """Generate instructions for MCP tools."""
    if not tools_map:
        return ""
    
    instructions = []
    for name, tool in tools_map.items():
        instructions.append(f"- {name}: {tool.description}")
    
    return "\\n".join(instructions)