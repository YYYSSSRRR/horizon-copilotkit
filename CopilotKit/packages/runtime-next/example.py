#!/usr/bin/env python3
"""
CopilotKit Runtime Next 示例

这个示例展示了如何创建一个完整的CopilotKit应用，包括：
- 定义自定义动作
- 设置适配器
- 启动服务器
"""

import asyncio
from typing import Dict, Any
from copilotkit_runtime import (
    CopilotRuntime,
    OpenAIAdapter,
    DeepSeekAdapter,
    CopilotRuntimeServer,
    Action,
    Parameter,
    ParameterType,
)


# 示例动作函数
async def get_weather(location: str) -> Dict[str, Any]:
    """
    获取指定地点的天气信息
    
    Args:
        location: 地点名称
        
    Returns:
        天气信息字典
    """
    # 模拟API调用
    await asyncio.sleep(0.1)
    
    return {
        "location": location,
        "temperature": "25°C",
        "condition": "晴朗",
        "humidity": "60%",
        "wind": "5 km/h"
    }


async def calculate(expression: str) -> Dict[str, Any]:
    """
    计算数学表达式
    
    Args:
        expression: 数学表达式
        
    Returns:
        计算结果
    """
    try:
        # 安全的数学表达式计算
        allowed_chars = "0123456789+-*/()."
        if all(c in allowed_chars or c.isspace() for c in expression):
            result = eval(expression)
            return {
                "expression": expression,
                "result": result,
                "success": True
            }
        else:
            return {
                "expression": expression,
                "error": "包含不允许的字符",
                "success": False
            }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


async def search_web(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    模拟网络搜索
    
    Args:
        query: 搜索查询
        limit: 结果数量限制
        
    Returns:
        搜索结果
    """
    # 模拟搜索结果
    await asyncio.sleep(0.2)
    
    results = []
    for i in range(min(limit, 3)):
        results.append({
            "title": f"关于 '{query}' 的搜索结果 {i+1}",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"这是关于 {query} 的详细信息..."
        })
    
    return {
        "query": query,
        "results": results,
        "total": len(results)
    }


def create_actions():
    """创建动作列表"""
    return [
        Action(
            name="get_weather",
            description="获取指定地点的天气信息",
            parameters=[
                Parameter(
                    name="location",
                    type=ParameterType.STRING,
                    description="地点名称，例如：北京、上海、广州",
                    required=True
                )
            ],
            handler=get_weather
        ),
        
        Action(
            name="calculate",
            description="计算数学表达式",
            parameters=[
                Parameter(
                    name="expression",
                    type=ParameterType.STRING,
                    description="要计算的数学表达式，例如：2+3*4",
                    required=True
                )
            ],
            handler=calculate
        ),
        
        Action(
            name="search_web",
            description="搜索网络信息",
            parameters=[
                Parameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="搜索查询词",
                    required=True
                ),
                Parameter(
                    name="limit",
                    type=ParameterType.NUMBER,
                    description="返回结果数量限制",
                    required=False,
                    default=5
                )
            ],
            handler=search_web
        ),
    ]


def create_adapter(provider: str = "openai") -> Any:
    """
    创建适配器
    
    Args:
        provider: 提供商名称 ("openai" 或 "deepseek")
        
    Returns:
        适配器实例
    """
    if provider.lower() == "deepseek":
        return DeepSeekAdapter(
            api_key="your-deepseek-api-key",  # 请替换为你的API密钥
            model="deepseek-chat",
            temperature=0.7
        )
    else:
        return OpenAIAdapter(
            api_key="your-openai-api-key",  # 请替换为你的API密钥
            model="gpt-4",
            temperature=0.7
        )


def main():
    """主函数"""
    print("🚀 启动 CopilotKit Runtime Next 示例服务器")
    print("=" * 50)
    
    # 创建动作
    actions = create_actions()
    print(f"📝 已注册 {len(actions)} 个动作:")
    for action in actions:
        print(f"  - {action.name}: {action.description}")
    
    # 创建适配器
    # 可以改为 "deepseek" 来使用 DeepSeek 适配器
    adapter = create_adapter("openai")
    print(f"🔌 使用适配器: {adapter}")
    
    # 创建运行时
    runtime = CopilotRuntime(actions=actions)
    print("⚙️ 运行时已创建")
    
    # 创建服务器
    server = CopilotRuntimeServer(
        runtime=runtime,
        service_adapter=adapter,
        title="CopilotKit Runtime Next 示例",
        cors_origins=["http://localhost:3000", "http://localhost:3001"]  # 允许前端访问
    )
    
    print("🌐 服务器配置完成")
    print("\n📡 API 端点:")
    print("  - GET  /api/health          - 健康检查")
    print("  - POST /api/chat            - 聊天完成")
    print("  - POST /api/chat/stream     - 流式聊天")
    print("  - GET  /api/actions         - 列出动作")
    print("  - POST /api/actions/execute - 执行动作")
    print("  - GET  /api/agents          - 列出代理")
    print()
    print("🚀 启动服务器...")
    print("💡 提示：确保已设置正确的API密钥！")
    print("🌍 访问: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print()
    
    # 启动服务器
    try:
        server.run(
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")
        print("💡 请检查API密钥配置和端口占用情况")


if __name__ == "__main__":
    main() 