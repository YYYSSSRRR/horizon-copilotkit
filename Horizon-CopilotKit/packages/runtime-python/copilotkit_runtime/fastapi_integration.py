"""
CopilotKit Python 运行时的 FastAPI 集成

本模块提供 FastAPI 集成，用于轻松部署 CopilotKit 运行时服务器。

功能包括：
- 自动挂载 GraphQL 端点
- 处理 HTTP 请求和 WebSocket 连接
- 提供便捷的服务器启动函数
- 支持自定义端点路径和配置
- 完整的 CORS 和中间件支持

使用示例：
    from copilotkit_runtime import CopilotRuntime, OpenAIAdapter, run_copilot_server
    
    runtime = CopilotRuntime(actions=[your_actions])
    adapter = OpenAIAdapter(api_key="your-key")
    
    # 启动服务器
    run_copilot_server(runtime, adapter, port=8000)
"""

from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse
from strawberry.fastapi import GraphQLRouter
import uvicorn

from .runtime import CopilotRuntime
from .adapters.base import CopilotServiceAdapter
from .graphql_schema import schema
from .types import GraphQLContext


class CopilotRuntimeFastAPI:
    """CopilotRuntime 的 FastAPI 集成类
    
    此类负责将 CopilotRuntime 集成到 FastAPI 应用中，提供：
    - GraphQL 端点的自动配置和挂载
    - 请求上下文的处理和传递
    - 运行时和适配器的管理
    
    使用示例:
        integration = CopilotRuntimeFastAPI(
            runtime=my_runtime,
            service_adapter=my_adapter,
            endpoint="/api/copilotkit"
        )
        integration.mount_graphql(app)
    """
    
    def __init__(
        self,
        runtime: CopilotRuntime,
        service_adapter: CopilotServiceAdapter,
        endpoint: str = "/api/copilotkit",
    ):
        """
        初始化 FastAPI 集成
        
        参数:
            runtime: CopilotRuntime 实例
            service_adapter: AI 服务适配器（如 OpenAIAdapter）
            endpoint: GraphQL 端点路径，默认为 "/api/copilotkit"
        """
        self.runtime = runtime
        self.service_adapter = service_adapter
        self.endpoint = endpoint
        # 创建 GraphQL 路由器，使用自定义上下文获取器
        self.graphql_router = GraphQLRouter(
            schema,
            context_getter=self._get_context,
        )
    
    def mount_graphql(self, app: FastAPI) -> None:
        """将 GraphQL 端点挂载到 FastAPI 应用
        
        参数:
            app: FastAPI 应用实例
        """
        app.include_router(
            self.graphql_router,
            prefix=self.endpoint,
        )
    
    async def _get_context(self, request: Request) -> Dict[str, Any]:
        """从请求中获取 GraphQL 上下文
        
        此方法为每个 GraphQL 请求创建上下文，包含：
        - 运行时实例
        - 服务适配器
        - 请求头和属性
        
        参数:
            request: FastAPI 请求对象
            
        返回:
            包含上下文信息的字典
        """
        return {
            "runtime": self.runtime,
            "service_adapter": self.service_adapter,
            "graphql_context": GraphQLContext(
                headers=dict(request.headers),
                properties={},
            ),
        }


def copilot_runtime_fastapi_endpoint(
    runtime: CopilotRuntime,
    service_adapter: CopilotServiceAdapter,
    endpoint: str = "/api/copilotkit",
) -> CopilotRuntimeFastAPI:
    """创建 CopilotRuntime 的 FastAPI 端点
    
    这是一个便捷函数，用于快速创建 FastAPI 集成实例。
    
    参数:
        runtime: CopilotRuntime 实例
        service_adapter: AI 服务适配器
        endpoint: GraphQL 端点路径
        
    返回:
        配置好的 CopilotRuntimeFastAPI 实例
    """
    return CopilotRuntimeFastAPI(
        runtime=runtime,
        service_adapter=service_adapter,
        endpoint=endpoint,
    )


def create_copilot_app(
    runtime: CopilotRuntime,
    service_adapter: CopilotServiceAdapter,
    endpoint: str = "/api/copilotkit",
    **kwargs: Any,
) -> FastAPI:
    """创建已挂载 CopilotRuntime 的 FastAPI 应用
    
    此函数创建一个完整的 FastAPI 应用，并自动挂载 CopilotRuntime 端点。
    适合需要自定义应用配置的场景。
    
    参数:
        runtime: CopilotRuntime 实例
        service_adapter: AI 服务适配器
        endpoint: GraphQL 端点路径
        **kwargs: 传递给 FastAPI 构造函数的额外参数
        
    返回:
        配置好的 FastAPI 应用实例
        
    使用示例:
        app = create_copilot_app(
            runtime=my_runtime,
            service_adapter=my_adapter,
            title="My CopilotKit API",
            description="AI-powered application"
        )
    """
    app = FastAPI(**kwargs)
    
    # 创建并挂载 CopilotRuntime 端点
    copilot_endpoint = copilot_runtime_fastapi_endpoint(
        runtime=runtime,
        service_adapter=service_adapter,
        endpoint=endpoint,
    )
    copilot_endpoint.mount_graphql(app)
    
    return app


async def run_copilot_server(
    runtime: CopilotRuntime,
    service_adapter: CopilotServiceAdapter,
    host: str = "0.0.0.0",
    port: int = 8000,
    endpoint: str = "/api/copilotkit",
    **kwargs: Any,
) -> None:
    """使用 uvicorn 运行 CopilotRuntime 服务器
    
    这是最简单的启动 CopilotKit 服务器的方法，适合开发和简单部署。
    
    参数:
        runtime: CopilotRuntime 实例
        service_adapter: AI 服务适配器（如 OpenAIAdapter、DeepSeekAdapter 等）
        host: 服务器主机地址，默认 "0.0.0.0"
        port: 服务器端口，默认 8000
        endpoint: GraphQL 端点路径，默认 "/api/copilotkit"
        **kwargs: 传递给 uvicorn.run 的额外参数
        
    使用示例:
        from copilotkit_runtime import CopilotRuntime, OpenAIAdapter, run_copilot_server
        
        runtime = CopilotRuntime(actions=[weather_action])
        adapter = OpenAIAdapter(api_key="your-key")
        
        # 启动服务器
        await run_copilot_server(
            runtime=runtime,
            adapter=adapter,
            port=8000,
            host="0.0.0.0"
        )
        
    注意:
        - 服务器将在指定端口上启动 HTTP 服务
        - GraphQL Playground 将在 {endpoint}/graphql 可用
        - 确保防火墙允许指定端口的访问
    """
    app = create_copilot_app(
        runtime=runtime,
        service_adapter=service_adapter,
        endpoint=endpoint,
    )
    
    uvicorn.run(app, host=host, port=port, **kwargs) 