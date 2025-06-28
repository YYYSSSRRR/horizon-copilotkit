"""
Exception classes for CopilotKit Python Runtime

This module defines all exception classes used throughout the runtime,
maintaining compatibility with the TypeScript version.
"""

from typing import Optional, Dict, Any


class CopilotKitError(Exception):
    """Base exception for CopilotKit errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class CopilotKitMisuseError(CopilotKitError):
    """Exception for misuse of CopilotKit APIs"""
    pass


class CopilotKitApiDiscoveryError(CopilotKitError):
    """Exception for API discovery errors"""
    pass


class CopilotKitAgentDiscoveryError(CopilotKitError):
    """Exception for agent discovery errors"""
    pass


class CopilotKitLowLevelError(CopilotKitError):
    """Exception for low-level runtime errors"""
    pass


class ResolvedCopilotKitError(CopilotKitError):
    """Exception for resolved CopilotKit errors"""
    
    def __init__(self, message: str, error_type: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        super().__init__(message, details) 