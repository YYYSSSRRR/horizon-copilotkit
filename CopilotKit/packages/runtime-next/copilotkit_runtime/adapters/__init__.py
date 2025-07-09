"""
适配器模块。
"""

from .base import *
from .deepseek import DeepSeekAdapter
from .openai import OpenAIAdapter

__all__ = [
    # 基础类型（从 types.adapters 重新导出）
    "CopilotServiceAdapter",
    "AdapterRequest", 
    "AdapterResponse",
    "AdapterCapabilities",
    "ProviderType",
    
    # 具体适配器实现
    "DeepSeekAdapter",
    "OpenAIAdapter",
] 