"""
CopilotKit Python 运行时的 DeepSeek 适配器示例

本示例演示了如何使用 DeepSeek 适配器的各种模型和配置选项。

DeepSeek 是一家专注于 AI 研究的公司，提供多种强大的大语言模型：
- deepseek-chat: 通用对话模型，适合日常聊天和任务执行
- deepseek-coder: 代码专用模型，优化了代码生成和理解能力
- deepseek-reasoner: 推理增强模型，适合复杂问题解决

运行前准备:
1. 获取 DeepSeek API Key: https://platform.deepseek.com/
2. 设置环境变量: export DEEPSEEK_API_KEY="your-deepseek-api-key"
3. 运行示例: python deepseek_example.py

功能演示:
- 不同 DeepSeek 模型的使用
- 多种适配器初始化方式
- 自定义 Actions 与 DeepSeek 的集成
- 服务器启动和配置
"""

import asyncio
import os
from typing import Dict, Any

from copilotkit_runtime import (
    CopilotRuntime,
    DeepSeekAdapter,
    Action,
    Parameter,
    run_copilot_server,
)
from openai import AsyncOpenAI


# 定义示例 Actions
def get_weather_action() -> Action:
    """创建天气查询 Action
    
    这个 Action 演示了如何创建带有多个参数的工具函数，
    包括必需参数和可选的枚举参数。
    """
    return Action(
        name="get_weather",
        description="获取指定位置的当前天气信息",
        parameters=[
            Parameter(
                name="location",
                type="string",
                description="城市和国家，例如 '北京, 中国' 或 'San Francisco, CA'",
                required=True,
            ),
            Parameter(
                name="unit",
                type="string",
                description="温度单位（摄氏度或华氏度）",
                enum=["celsius", "fahrenheit"],
                default="celsius",
            ),
        ],
        handler=get_weather_handler,
    )


async def get_weather_handler(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """天气查询处理函数（模拟实现）
    
    在实际应用中，你会调用真实的天气 API（如 OpenWeatherMap）。
    这里为了演示目的，返回模拟的天气数据。
    """
    # 在真实应用中，这里会调用天气 API
    temp = 22 if unit == "celsius" else 72
    return {
        "location": location,
        "temperature": temp,
        "unit": unit,
        "condition": "晴天",
        "humidity": "65%",
        "wind_speed": "10 km/h",
    }


def get_code_analysis_action() -> Action:
    """Analyze code quality and suggest improvements."""
    return Action(
        name="analyze_code",
        description="Analyze code quality and provide suggestions for improvement",
        parameters=[
            Parameter(
                name="code",
                type="string",
                description="The code to analyze",
                required=True,
            ),
            Parameter(
                name="language",
                type="string",
                description="Programming language of the code",
                enum=["python", "javascript", "typescript", "java", "cpp", "go"],
                default="python",
            ),
        ],
        handler=analyze_code_handler,
    )


async def analyze_code_handler(code: str, language: str = "python") -> Dict[str, Any]:
    """Mock code analysis handler."""
    # In a real app, you would use static analysis tools
    return {
        "language": language,
        "lines_of_code": len(code.split("\n")),
        "suggestions": [
            "Consider adding type hints for better code clarity",
            "Add docstrings to functions for better documentation",
            "Consider breaking down large functions into smaller ones",
        ],
        "quality_score": 8.5,
        "complexity": "Medium",
    }


def create_deepseek_runtime() -> CopilotRuntime:
    """Create a CopilotRuntime with DeepSeek adapter."""
    
    # Define actions
    actions = [
        get_weather_action(),
        get_code_analysis_action(),
    ]
    
    # Create runtime
    runtime = CopilotRuntime(actions=actions)
    
    return runtime


def create_deepseek_adapter(model: str = "deepseek-chat") -> DeepSeekAdapter:
    """Create DeepSeek adapter with different configurations."""
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Method 1: Using API key directly
    adapter = DeepSeekAdapter(
        api_key=api_key,
        model=model,
        disable_parallel_tool_calls=False,  # Enable parallel tool calls for efficiency
    )
    
    return adapter


def create_deepseek_adapter_with_openai() -> DeepSeekAdapter:
    """Create DeepSeek adapter using pre-configured OpenAI client."""
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    
    # Method 2: Using pre-configured OpenAI client
    deepseek_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        default_headers={
            "User-Agent": "MyApp-DeepSeek-Integration",
        },
    )
    
    adapter = DeepSeekAdapter(
        openai=deepseek_client,
        model="deepseek-coder",  # Use the code-specialized model
    )
    
    return adapter


async def main():
    """Main example function."""
    print("🚀 Starting DeepSeek Adapter Example...")
    
    # Create runtime
    runtime = create_deepseek_runtime()
    
    # Example 1: Chat model for general conversation
    print("\n📱 Example 1: Using deepseek-chat model")
    chat_adapter = create_deepseek_adapter("deepseek-chat")
    
    # Example 2: Coder model for code-related tasks
    print("💻 Example 2: Using deepseek-coder model")
    coder_adapter = create_deepseek_adapter("deepseek-coder")
    
    # Example 3: Reasoner model for complex reasoning
    print("🧠 Example 3: Using deepseek-reasoner model")
    reasoner_adapter = create_deepseek_adapter("deepseek-reasoner")
    
    # Example 4: Custom OpenAI client configuration
    print("⚙️  Example 4: Using custom OpenAI client")
    custom_adapter = create_deepseek_adapter_with_openai()
    
    print("\n✅ All DeepSeek adapters created successfully!")
    print("\n📚 Available models:")
    print("  - deepseek-chat: General conversation and task execution")
    print("  - deepseek-coder: Code generation and analysis")
    print("  - deepseek-reasoner: Complex reasoning and problem solving")
    
    # Start server with chat adapter (you can switch to any adapter)
    print(f"\n🌐 Starting server with deepseek-chat adapter on port 8000...")
    print("You can now connect your frontend to http://localhost:8000")
    
    await run_copilot_server(
        runtime=runtime,
        adapter=chat_adapter,
        port=8000,
        host="0.0.0.0",
    )


if __name__ == "__main__":
    # Set up environment
    print("🔧 DeepSeek Environment Setup:")
    print("Make sure to set your DEEPSEEK_API_KEY environment variable")
    print("Example: export DEEPSEEK_API_KEY='sk-your-deepseek-api-key'")
    print()
    
    # Check if API key is set
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ Error: DEEPSEEK_API_KEY environment variable not found")
        print("Please set your DeepSeek API key before running this example")
        exit(1)
    
    # Run the example
    asyncio.run(main()) 