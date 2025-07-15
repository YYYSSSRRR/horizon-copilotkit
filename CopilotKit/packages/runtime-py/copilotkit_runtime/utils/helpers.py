"""
辅助函数

对标TypeScript runtime中的工具函数
"""

import uuid
import json
from typing import Any, Dict, List, Optional

from copilotkit_runtime.types import (
    ActionInput,
    Message,
    MessageRole,
    MessageType,
    Parameter
)


def random_id() -> str:
    """生成随机ID"""
    return str(uuid.uuid4())


def convert_actions_to_tools(actions: List[ActionInput]) -> List[Dict[str, Any]]:
    """
    将动作列表转换为OpenAI工具格式
    
    对标TypeScript的convertActionInputToOpenAITool函数
    """
    tools = []
    
    for action in actions:
        # 构建参数schema
        properties = {}
        required = []
        
        for param in action.parameters:
            param_schema = {
                "type": param.type,
            }
            
            if param.description:
                param_schema["description"] = param.description
            
            if param.enum:
                param_schema["enum"] = param.enum
            
            if param.default is not None:
                param_schema["default"] = param.default
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        # 构建工具定义
        tool = {
            "type": "function",
            "function": {
                "name": action.name,
                "description": action.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        
        tools.append(tool)
    
    return tools


def convert_messages_to_openai(
    messages: List[Message],
    keep_system_role: bool = False
) -> List[Dict[str, Any]]:
    """
    将消息列表转换为OpenAI格式
    
    对标TypeScript的convertMessageToOpenAIMessage函数
    """
    openai_messages = []
    
    for message in messages:
        if message.is_text_message():
            role = message.role.value
            
            # 处理system角色
            if message.role == MessageRole.SYSTEM and not keep_system_role:
                role = "developer"
            
            openai_message = {
                "role": role,
                "content": message.content
            }
            
        elif message.is_image_message():
            openai_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{message.format};base64,{message.bytes}"
                        }
                    }
                ]
            }
            
        elif message.is_action_execution_message():
            openai_message = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": message.id,
                        "type": "function",
                        "function": {
                            "name": message.name,
                            "arguments": json.dumps(message.arguments)
                        }
                    }
                ]
            }
            
        elif message.is_result_message():
            openai_message = {
                "role": "tool",
                "content": message.result,
                "tool_call_id": message.action_execution_id
            }
            
        else:
            # 未知消息类型，跳过
            continue
        
        openai_messages.append(openai_message)
    
    return openai_messages


def limit_messages_to_token_count(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str,
    max_tokens: int = 16000
) -> List[Dict[str, Any]]:
    """
    限制消息的token数量
    
    简化版本的token限制逻辑
    """
    # 简化实现：如果消息太多，保留最近的消息
    if len(messages) > 20:
        # 保留系统消息和最近的消息
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        recent_messages = messages[-15:]  # 保留最近15条消息
        
        # 合并并去重
        limited_messages = system_messages
        for msg in recent_messages:
            if msg not in limited_messages:
                limited_messages.append(msg)
        
        return limited_messages
    
    return messages


def create_parameter_schema(params: List[Parameter]) -> Dict[str, Any]:
    """
    创建参数的JSON Schema
    """
    properties = {}
    required = []
    
    for param in params:
        param_schema = {"type": param.type}
        
        if param.description:
            param_schema["description"] = param.description
        
        if param.enum:
            param_schema["enum"] = param.enum
        
        properties[param.name] = param_schema
        
        if param.required:
            required.append(param.name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required
    } 