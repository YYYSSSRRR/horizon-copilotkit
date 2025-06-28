#!/usr/bin/env python3
"""
CopilotKit Python 运行时基础示例

本示例演示了如何使用 CopilotKit Python 运行时与 OpenAI 适配器和基础 Actions。

功能演示:
- 创建自定义 Actions（工具函数）
- 配置中间件进行请求处理
- 使用 OpenAI 适配器
- 启动 FastAPI 服务器

运行方式:
1. 设置环境变量: export OPENAI_API_KEY="your-api-key"
2. 运行脚本: python basic_example.py
3. 访问 http://localhost:8000/api/copilotkit/graphql 查看 GraphQL Playground
"""

import os
import asyncio
from copilotkit_runtime import (
    CopilotRuntime,
    OpenAIAdapter,
    Action,
    Parameter,
    Middleware,
    run_copilot_server,
)


def get_weather(location: str) -> str:
    """获取指定位置的天气信息
    
    这是一个示例 Action，模拟天气查询功能。
    在实际应用中，你会调用真实的天气 API。
    """
    return f"{location} 的天气是晴天，温度 22°C"


def calculate_sum(a: float, b: float) -> float:
    """计算两个数字的和
    
    这是一个简单的数学计算 Action 示例。
    """
    return a + b


async def before_request(options):
    """请求前中间件函数
    
    在每个请求处理前调用，可用于日志记录、认证等。
    """
    print(f"正在处理线程 {options.thread_id} 的请求")


async def after_request(options):
    """请求后中间件函数
    
    在每个请求处理后调用，可用于清理、统计等。
    """
    print(f"线程 {options.thread_id} 的请求处理完成")


def main():
    """主函数，用于运行 CopilotKit 服务器"""
    
    # 定义 Actions（可供 AI 调用的工具函数）
    actions = [
        Action(
            name="get_weather",
            description="获取指定位置的天气信息",
            parameters=[
                Parameter(
                    name="location",
                    type="string",
                    description="要查询天气的位置",
                    required=True,
                )
            ],
            handler=get_weather,
        ),
        Action(
            name="calculate_sum",
            description="计算两个数字的和",
            parameters=[
                Parameter(
                    name="a",
                    type="number",
                    description="第一个数字",
                    required=True,
                ),
                Parameter(
                    name="b",
                    type="number",
                    description="第二个数字",
                    required=True,
                ),
            ],
            handler=calculate_sum,
        ),
    ]
    
    # 创建中间件配置
    middleware = Middleware(
        on_before_request=before_request,  # 请求前处理
        on_after_request=after_request,   # 请求后处理
    )
    
    # 创建运行时实例
    runtime = CopilotRuntime(
        actions=actions,      # 注册 Actions
        middleware=middleware, # 注册中间件
    )
    
    # 创建 OpenAI 适配器
    adapter = OpenAIAdapter(
        api_key=os.getenv("OPENAI_API_KEY"),  # 从环境变量获取 API Key
        model="gpt-4o",  # 使用 GPT-4o 模型
    )
    
    # 启动服务器
    print("正在启动 CopilotKit Python Runtime 服务器...")
    print("GraphQL 端点: http://localhost:8000/api/copilotkit")
    print("GraphQL Playground: http://localhost:8000/api/copilotkit/graphql")
    
    run_copilot_server(
        runtime=runtime,
        service_adapter=adapter,
        host="0.0.0.0",
        port=8000,
        endpoint="/api/copilotkit",
    )


if __name__ == "__main__":
    main() 