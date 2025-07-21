"""Exception definitions for CopilotKit Runtime."""

from typing import Any, Dict, List, Optional


class CopilotKitError(Exception):
    """Base CopilotKit error."""
    
    def __init__(self, message: str = "", **kwargs):
        self.message = message
        super().__init__(message)


class CopilotKitMisuseError(CopilotKitError):
    """Error for misuse of CopilotKit APIs."""
    pass


class CopilotKitAgentDiscoveryError(CopilotKitError):
    """Error for agent discovery failures."""
    
    def __init__(self, agent_name: Optional[str] = None, available_agents: Optional[List[Dict[str, str]]] = None, **kwargs):
        self.agent_name = agent_name
        self.available_agents = available_agents or []
        message = f"Agent discovery failed"
        if agent_name:
            message += f" for agent '{agent_name}'"
        super().__init__(message, **kwargs)


class CopilotKitApiDiscoveryError(CopilotKitError):
    """Error for API discovery failures."""
    
    def __init__(self, url: str, **kwargs):
        self.url = url
        super().__init__(f"API discovery failed for URL: {url}", **kwargs)


class CopilotKitLowLevelError(CopilotKitError):
    """Low-level error wrapper."""
    
    def __init__(self, error: Exception, url: Optional[str] = None, **kwargs):
        self.original_error = error
        self.url = url
        message = f"Low-level error: {str(error)}"
        if url:
            message += f" (URL: {url})"
        super().__init__(message, **kwargs)


class ResolvedCopilotKitError(CopilotKitError):
    """Resolved error with status information."""
    
    def __init__(self, status: int, url: str, is_remote_endpoint: bool = False, **kwargs):
        self.status = status
        self.url = url
        self.is_remote_endpoint = is_remote_endpoint
        message = f"HTTP {status} error for {url}"
        if is_remote_endpoint:
            message += " (remote endpoint)"
        super().__init__(message, **kwargs)