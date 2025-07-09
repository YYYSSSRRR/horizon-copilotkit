"""
扩展相关类型定义

定义了 CopilotKit 运行时的扩展系统类型。
"""

from typing import Any, Dict
from dataclasses import dataclass, field


@dataclass
class Extensions:
    """扩展配置"""
    data: Dict[str, Any] = field(default_factory=dict) 