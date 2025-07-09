#!/usr/bin/env python3
"""
简单的运行时测试
"""

import asyncio
import os
from copilotkit_runtime import (
    CopilotRuntime,
    OpenAIAdapter,
    DeepSeekAdapter,
    TextMessage,
    MessageRole,
    Action,
    Parameter,
    ParameterType
)


async def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试CopilotKit Runtime Next基本功能...")
    
    # 创建一个简单的动作
    test_action = Action(
        name="get_weather",
        description="获取天气信息",
        parameters=[
            Parameter(
                name="city",
                type=ParameterType.STRING,
                description="城市名称",
                required=True
            )
        ]
    )
    
    # 创建测试消息
    test_message = TextMessage(
        role=MessageRole.USER,
        content="Hello, how are you?"
    )
    
    print(f"✅ 创建测试消息: {test_message.content}")
    print(f"✅ 创建测试动作: {test_action.name}")
    
    # 测试适配器创建（不需要真实的API密钥）
    try:
        openai_adapter = OpenAIAdapter(api_key="test-key")
        print(f"✅ OpenAI适配器创建成功: {openai_adapter.get_provider_name()}")
    except Exception as e:
        print(f"❌ OpenAI适配器创建失败: {e}")
    
    try:
        deepseek_adapter = DeepSeekAdapter(api_key="test-key")
        print(f"✅ DeepSeek适配器创建成功: {deepseek_adapter.get_provider_name()}")
    except Exception as e:
        print(f"❌ DeepSeek适配器创建失败: {e}")
    
    # 测试运行时创建
    try:
        runtime = CopilotRuntime(
            service_adapter=openai_adapter,
            actions=[test_action]
        )
        print(f"✅ CopilotRuntime创建成功")
    except Exception as e:
        print(f"❌ CopilotRuntime创建失败: {e}")
    
    print("🎉 基本功能测试完成！")


async def test_server_integration():
    """测试服务器集成"""
    print("\n🌐 测试服务器集成...")
    
    try:
        from copilotkit_runtime import CopilotRuntimeServer, create_copilot_app
        
        # 创建适配器
        adapter = OpenAIAdapter(api_key="test-key")
        
        # 创建运行时
        runtime = CopilotRuntime(service_adapter=adapter)
        
        # 创建服务器
        server = CopilotRuntimeServer(runtime=runtime)
        
        # 创建FastAPI应用
        app = create_copilot_app(runtime)
        
        print("✅ 服务器集成测试成功")
        print(f"✅ FastAPI应用创建成功: {type(app)}")
        
    except Exception as e:
        print(f"❌ 服务器集成测试失败: {e}")


def test_json_serialization():
    """测试JSON序列化"""
    print("\n📄 测试JSON序列化...")
    
    try:
        # 测试消息序列化
        message = TextMessage(
            role=MessageRole.USER,
            content="Test message"
        )
        
        json_data = message.to_json()
        print(f"✅ 消息序列化成功: {json_data}")
        
        # 测试动作序列化
        action = Action(
            name="test_action",
            description="Test action",
            parameters=[
                Parameter(
                    name="param1",
                    type=ParameterType.STRING,
                    description="Test parameter"
                )
            ]
        )
        
        action_dict = action.to_dict()
        print(f"✅ 动作序列化成功: {action_dict}")
        
    except Exception as e:
        print(f"❌ JSON序列化测试失败: {e}")


def main():
    """主函数"""
    print("🚀 CopilotKit Runtime Next - 功能测试")
    print("=" * 50)
    
    # 运行异步测试
    asyncio.run(test_basic_functionality())
    asyncio.run(test_server_integration())
    
    # 运行同步测试
    test_json_serialization()
    
    print("\n" + "=" * 50)
    print("🎯 测试完成！")
    print("\n💡 提示：")
    print("- 使用 'python -m copilotkit_runtime.cli --help' 查看CLI选项")
    print("- 设置环境变量 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 来测试真实API")
    print("- 运行 'python -m copilotkit_runtime.cli --provider openai --api-key YOUR_KEY' 启动服务器")


if __name__ == "__main__":
    main() 