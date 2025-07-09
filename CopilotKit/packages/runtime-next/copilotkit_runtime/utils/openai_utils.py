"""
OpenAI工具函数。
"""

from typing import Any, Dict, List
from ..types.messages import Message, TextMessage, MessageRole
from ..types.actions import Action


def convert_message_to_openai(message: Message) -> Dict[str, Any]:
    """
    将消息转换为OpenAI格式
    
    Args:
        message: 消息对象
        
    Returns:
        OpenAI格式的消息
    """
    if isinstance(message, TextMessage):
        return {
            "role": message.role.value,
            "content": message.content
        }
    
    # 其他类型的消息处理
    return {
        "role": "user",
        "content": str(message)
    }


def convert_messages_to_openai(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    将消息列表转换为OpenAI格式
    
    Args:
        messages: 消息列表
        
    Returns:
        OpenAI格式的消息列表
    """
    return [convert_message_to_openai(msg) for msg in messages]


def convert_action_to_openai_tool(action: Action) -> Dict[str, Any]:
    """
    将动作转换为OpenAI工具格式
    
    Args:
        action: 动作对象
        
    Returns:
        OpenAI工具格式
    """
    return {
        "type": "function",
        "function": {
            "name": action.name,
            "description": action.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


def convert_actions_to_openai_tools(actions: List[Action]) -> List[Dict[str, Any]]:
    """
    将动作列表转换为OpenAI工具格式
    
    Args:
        actions: 动作列表
        
    Returns:
        OpenAI工具格式列表
    """
    return [convert_action_to_openai_tool(action) for action in actions] 