#!/usr/bin/env python3
"""
CopilotKit Runtime Next 服务器启动脚本
"""

import os
import uvicorn
from copilotkit_runtime import (
    CopilotRuntime,
    OpenAIAdapter,
    DeepSeekAdapter,
    create_copilot_app,
    Action,
    Parameter,
    ParameterType
)


def create_test_action():
    """创建一个测试动作"""
    async def get_weather(arguments):
        """获取天气信息"""
        city = arguments.get("city", "北京")
        return f"今天{city}的天气是晴天，温度25°C"
    
    return Action(
        name="get_weather",
        description="获取指定城市的天气信息",
        parameters=[
            Parameter(
                name="city",
                type=ParameterType.STRING,
                description="城市名称",
                required=True
            )
        ],
        handler=get_weather
    )


def main():
    """主函数"""
    print("🚀 启动 CopilotKit Runtime Next 服务器...")
    
    # 获取API密钥
    openai_api_key = os.getenv("OPENAI_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # 选择适配器
    if openai_api_key:
        print("✅ 使用 OpenAI 适配器")
        adapter = OpenAIAdapter(api_key=openai_api_key)
    elif deepseek_api_key:
        print("✅ 使用 DeepSeek 适配器")
        adapter = DeepSeekAdapter(api_key=deepseek_api_key)
    else:
        print("⚠️  未找到API密钥，使用测试适配器")
        adapter = OpenAIAdapter(api_key="test-key")
    
    # 创建测试动作
    test_action = create_test_action()
    
    # 创建运行时
    runtime = CopilotRuntime(
        service_adapter=adapter,
        actions=[test_action]
    )
    
    # 创建FastAPI应用
    app = create_copilot_app(runtime)
    
    print("🌐 服务器启动信息:")
    print("- 地址: http://localhost:8000")
    print("- API文档: http://localhost:8000/docs")
    print("- 健康检查: http://localhost:8000/health")
    print("- 聊天端点: POST http://localhost:8000/copilotkit")
    print("\n按 Ctrl+C 停止服务器")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main() 