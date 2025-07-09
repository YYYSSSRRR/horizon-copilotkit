"""
通用工具函数。
"""

import uuid
import re
from typing import Optional


def generate_id() -> str:
    """
    生成唯一ID
    
    Returns:
        UUID字符串
    """
    return str(uuid.uuid4())


def detect_provider(model_name: str) -> Optional[str]:
    """
    根据模型名称检测AI服务提供商
    
    Args:
        model_name: 模型名称
        
    Returns:
        提供商名称或None
    """
    model_name_lower = model_name.lower()
    
    # OpenAI模型
    if any(pattern in model_name_lower for pattern in ["gpt-", "davinci", "curie", "babbage", "ada"]):
        return "openai"
    
    # DeepSeek模型
    if "deepseek" in model_name_lower:
        return "deepseek"
    
    # Claude模型 
    if "claude" in model_name_lower:
        return "anthropic"
        
    # Gemini模型
    if "gemini" in model_name_lower:
        return "google"
    
    # Llama模型
    if "llama" in model_name_lower:
        return "meta"
    
    return None


def safe_json_loads(text: str, default=None):
    """
    安全的JSON解析
    
    Args:
        text: 要解析的JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        解析结果或默认值
    """
    try:
        import json
        return json.loads(text)
    except:
        return default


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_url(url: str) -> bool:
    """
    检查URL是否有效
    
    Args:
        url: 要检查的URL
        
    Returns:
        是否有效
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None 