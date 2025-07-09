"""
适配器基础类型重新导出。
"""

from ..types.adapters import CopilotServiceAdapter, AdapterRequest, AdapterResponse, EventSource

__all__ = [
    "CopilotServiceAdapter",
    "AdapterRequest", 
    "AdapterResponse",
    "EventSource",
] 