"""
Utility functions for CopilotKit Python Runtime

This module provides utility functions used throughout the runtime.
"""

import uuid
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


def random_id() -> str:
    """Generate a random ID"""
    return str(uuid.uuid4())


def random_short_id() -> str:
    """Generate a short random ID"""
    return str(uuid.uuid4())[:8]


def current_timestamp() -> datetime:
    """Get current timestamp"""
    return datetime.now()


def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_stringify(obj: Any) -> str:
    """Safely stringify object to JSON"""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)


def flatten_tool_calls_no_duplicates(tools_by_priority: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten tool calls and remove duplicates, maintaining priority order"""
    seen_names = set()
    result = []
    
    for tool in tools_by_priority:
        name = tool.get("name")
        if name and name not in seen_names:
            seen_names.add(name)
            result.append(tool)
    
    return result


def action_parameters_to_json_schema(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert action parameters to JSON schema format"""
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    for param in parameters:
        name = param.get("name")
        if not name:
            continue
        
        param_schema = {
            "type": param.get("type", "string"),
            "description": param.get("description", "")
        }
        
        if param.get("enum"):
            param_schema["enum"] = param["enum"]
        
        schema["properties"][name] = param_schema
        
        if param.get("required", False):
            schema["required"].append(name)
    
    return schema


def convert_message_input_to_message(message_input: Dict[str, Any]) -> Dict[str, Any]:
    """Convert message input to message format"""
    message = {
        "id": message_input.get("id", random_id()),
        "created_at": message_input.get("created_at", current_timestamp()),
    }
    
    # Copy message type fields
    for field in ["text_message", "action_execution_message", "result_message", 
                  "agent_state_message", "image_message"]:
        if field in message_input:
            message[field] = message_input[field]
    
    return message


def detect_provider(adapter_class_name: str) -> Optional[str]:
    """Detect provider from adapter class name"""
    if "OpenAI" in adapter_class_name:
        return "openai"
    elif "Anthropic" in adapter_class_name:
        return "anthropic"
    elif "Google" in adapter_class_name:
        return "google"
    elif "LangChain" in adapter_class_name:
        return "langchain"
    else:
        return None 