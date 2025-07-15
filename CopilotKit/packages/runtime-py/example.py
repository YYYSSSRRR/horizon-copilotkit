#!/usr/bin/env python3
"""
CopilotKit Python Runtime 示例

展示如何使用CopilotKit Python Runtime与DeepSeek适配器
"""

import asyncio
import logging
import os
from copilotkit_runtime import CopilotRuntime
from copilotkit_runtime.adapters.deepseek import DeepSeekAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def get_weather(city: str) -> str:
    """获取天气信息的示例动作"""
    # 这里可以调用真实的天气API
    weather_data = {
        "北京": "晴天，温度15°C",
        "上海": "多云，温度18°C", 
        "深圳": "小雨，温度22°C"
    }
    
    result = weather_data.get(city, f"{city}的天气信息暂时无法获取")
    logger.info(f"🌤️ 获取天气: {city} -> {result}")
    return result


async def calculate(expression: str) -> str:
    """计算表达式的示例动作"""
    try:
        # 简单的安全计算（生产环境需要更严格的验证）
        if any(op in expression for op in ['import', 'exec', 'eval', '__']):
            return "不安全的表达式"
        
        result = eval(expression)
        logger.info(f"🧮 计算: {expression} = {result}")
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


def create_runtime() -> CopilotRuntime:
    """创建并配置CopilotRuntime"""
    # 创建运行时实例
    runtime = CopilotRuntime()
    
    # 配置DeepSeek适配器
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("⚠️ 未设置DEEPSEEK_API_KEY环境变量，将使用空适配器")
    else:
        deepseek_adapter = DeepSeekAdapter(
            api_key=api_key,
            model="deepseek-chat"
        )
        runtime.use(deepseek_adapter)
        logger.info("✅ 配置DeepSeek适配器成功")
    
    # 注册动作
    runtime.action(
        name="get_weather",
        description="获取指定城市的天气信息",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        },
        handler=get_weather
    )
    
    runtime.action(
        name="calculate",
        description="计算数学表达式",
        parameters={
            "type": "object", 
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式"
                }
            },
            "required": ["expression"]
        },
        handler=calculate
    )
    
    logger.info("🎯 注册动作完成")
    return runtime


def main():
    """主函数"""
    logger.info("🚀 启动CopilotKit Python Runtime示例")
    
    # 创建运行时
    runtime = create_runtime()
    
    # 启动服务器
    logger.info("📡 启动服务器...")
    logger.info("🌐 访问 http://localhost:8000 查看API")
    logger.info("📖 访问 http://localhost:8000/docs 查看自动生成的API文档")
    
    try:
        runtime.start(
            host="0.0.0.0",
            port=8000,
            reload=False  # 生产环境设为False
        )
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")


if __name__ == "__main__":
    main() 