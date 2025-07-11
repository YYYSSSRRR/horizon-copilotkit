"""
增强的中间件系统实现。

实现了类似 TypeScript 版本的中间件能力，包括：
- 输出消息 Promise 支持
- 复杂的中间件管道
- 错误处理和恢复
- 异步中间件链
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from datetime import datetime
from abc import ABC, abstractmethod

from ..types.messages import Message
from ..types.runtime import CopilotRuntimeRequest, CopilotRuntimeResponse
from ..events.enhanced_runtime_events import MessageStatus, SuccessMessageStatus, FailedMessageStatus

logger = logging.getLogger(__name__)


class MiddlewareContext:
    """中间件上下文"""
    def __init__(self, 
                 thread_id: str,
                 run_id: Optional[str] = None,
                 properties: Optional[Dict[str, Any]] = None,
                 url: Optional[str] = None):
        self.thread_id = thread_id
        self.run_id = run_id
        self.properties = properties or {}
        self.url = url
        self.metadata: Dict[str, Any] = {}
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default=None):
        """获取元数据"""
        return self.metadata.get(key, default)


class BeforeRequestOptions:
    """请求前选项"""
    def __init__(self,
                 context: MiddlewareContext,
                 input_messages: List[Message],
                 actions: Optional[List[Any]] = None):
        self.context = context
        self.input_messages = input_messages
        self.actions = actions or []
        self.timestamp = datetime.now()


class AfterRequestOptions:
    """请求后选项"""
    def __init__(self,
                 context: MiddlewareContext,
                 input_messages: List[Message],
                 output_messages: List[Message],
                 status: MessageStatus,
                 execution_time: float):
        self.context = context
        self.input_messages = input_messages
        self.output_messages = output_messages
        self.status = status
        self.execution_time = execution_time
        self.timestamp = datetime.now()


class MiddlewareResult:
    """中间件执行结果"""
    def __init__(self, 
                 success: bool = True,
                 error: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 modified_messages: Optional[List[Message]] = None):
        self.success = success
        self.error = error
        self.metadata = metadata or {}
        self.modified_messages = modified_messages


class BaseMiddleware(ABC):
    """中间件基类"""
    
    @abstractmethod
    async def before_request(self, options: BeforeRequestOptions) -> MiddlewareResult:
        """请求前处理"""
        pass
    
    @abstractmethod
    async def after_request(self, options: AfterRequestOptions) -> MiddlewareResult:
        """请求后处理"""
        pass
    
    async def on_error(self, error: Exception, context: MiddlewareContext) -> MiddlewareResult:
        """错误处理"""
        return MiddlewareResult(success=False, error=str(error))


class LoggingMiddleware(BaseMiddleware):
    """日志中间件"""
    
    def __init__(self, level: int = logging.INFO):
        self.logger = logging.getLogger(f"{__name__}.LoggingMiddleware")
        self.logger.setLevel(level)
    
    async def before_request(self, options: BeforeRequestOptions) -> MiddlewareResult:
        """记录请求开始"""
        self.logger.info(
            f"🚀 Request started - Thread: {options.context.thread_id}, "
            f"Messages: {len(options.input_messages)}, "
            f"Actions: {len(options.actions)}"
        )
        return MiddlewareResult()
    
    async def after_request(self, options: AfterRequestOptions) -> MiddlewareResult:
        """记录请求完成"""
        self.logger.info(
            f"✅ Request completed - Thread: {options.context.thread_id}, "
            f"Output Messages: {len(options.output_messages)}, "
            f"Status: {options.status.code}, "
            f"Time: {options.execution_time:.3f}s"
        )
        return MiddlewareResult()


class MetricsMiddleware(BaseMiddleware):
    """指标收集中间件"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "message_counts": {"input": 0, "output": 0},
            "action_executions": 0
        }
    
    async def before_request(self, options: BeforeRequestOptions) -> MiddlewareResult:
        """开始计时"""
        self.metrics["total_requests"] += 1
        self.metrics["message_counts"]["input"] += len(options.input_messages)
        
        # 在上下文中保存开始时间
        options.context.set_metadata("start_time", datetime.now())
        return MiddlewareResult()
    
    async def after_request(self, options: AfterRequestOptions) -> MiddlewareResult:
        """更新指标"""
        if options.status.code == "success":
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        self.metrics["total_execution_time"] += options.execution_time
        self.metrics["average_execution_time"] = (
            self.metrics["total_execution_time"] / self.metrics["total_requests"]
        )
        self.metrics["message_counts"]["output"] += len(options.output_messages)
        
        # 统计动作执行
        action_count = sum(1 for msg in options.output_messages 
                          if msg.type == "action_execution")
        self.metrics["action_executions"] += action_count
        
        return MiddlewareResult()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics.copy()


class AuthenticationMiddleware(BaseMiddleware):
    """认证中间件"""
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        self.api_keys = set(api_keys or [])
    
    async def before_request(self, options: BeforeRequestOptions) -> MiddlewareResult:
        """验证API密钥"""
        if not self.api_keys:
            return MiddlewareResult()  # 没有配置密钥时跳过验证
        
        api_key = options.context.properties.get("api_key")
        if not api_key or api_key not in self.api_keys:
            return MiddlewareResult(
                success=False,
                error="Invalid API key"
            )
        
        return MiddlewareResult()
    
    async def after_request(self, options: AfterRequestOptions) -> MiddlewareResult:
        """请求后不需要处理"""
        return MiddlewareResult()


class RateLimitMiddleware(BaseMiddleware):
    """限流中间件"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.request_timestamps: Dict[str, List[datetime]] = {}
    
    async def before_request(self, options: BeforeRequestOptions) -> MiddlewareResult:
        """检查限流"""
        thread_id = options.context.thread_id
        now = datetime.now()
        
        # 初始化或清理过期的时间戳
        if thread_id not in self.request_timestamps:
            self.request_timestamps[thread_id] = []
        
        # 移除超过1分钟的请求
        cutoff_time = now.timestamp() - 60
        self.request_timestamps[thread_id] = [
            ts for ts in self.request_timestamps[thread_id]
            if ts.timestamp() > cutoff_time
        ]
        
        # 检查是否超过限制
        if len(self.request_timestamps[thread_id]) >= self.max_requests:
            return MiddlewareResult(
                success=False,
                error=f"Rate limit exceeded: {self.max_requests} requests per minute"
            )
        
        # 记录当前请求
        self.request_timestamps[thread_id].append(now)
        return MiddlewareResult()
    
    async def after_request(self, options: AfterRequestOptions) -> MiddlewareResult:
        """请求后不需要处理"""
        return MiddlewareResult()


class EnhancedMiddlewareChain:
    """
    增强的中间件链
    
    支持类似 TypeScript 版本的复杂中间件管道
    """
    
    def __init__(self, middlewares: Optional[List[BaseMiddleware]] = None):
        self.middlewares = middlewares or []
        self.output_message_futures: Dict[str, asyncio.Future[List[Message]]] = {}
    
    def add_middleware(self, middleware: BaseMiddleware):
        """添加中间件"""
        self.middlewares.append(middleware)
    
    def remove_middleware(self, middleware: BaseMiddleware):
        """移除中间件"""
        if middleware in self.middlewares:
            self.middlewares.remove(middleware)
    
    async def process_request(self, 
                            request: CopilotRuntimeRequest,
                            output_messages_future: asyncio.Future[List[Message]]) -> MiddlewareResult:
        """
        处理请求（支持输出消息 Future）
        
        Args:
            request: 运行时请求
            output_messages_future: 输出消息的 Future
            
        Returns:
            中间件处理结果
        """
        context = MiddlewareContext(
            thread_id=request.thread_id or "unknown",
            run_id=request.run_id,
            properties=request.context.properties if request.context else {},
            url=request.context.url if request.context else None
        )
        
        start_time = datetime.now()
        
        try:
            # 执行前置中间件
            before_options = BeforeRequestOptions(
                context=context,
                input_messages=request.messages,
                actions=[]  # TODO: 从请求中获取动作
            )
            
            for middleware in self.middlewares:
                result = await middleware.before_request(before_options)
                if not result.success:
                    return result
                
                # 应用中间件修改
                if result.modified_messages:
                    before_options.input_messages = result.modified_messages
                
                # 合并元数据
                context.metadata.update(result.metadata)
            
            # 等待输出消息完成
            try:
                output_messages = await output_messages_future
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # 执行后置中间件
                after_options = AfterRequestOptions(
                    context=context,
                    input_messages=before_options.input_messages,
                    output_messages=output_messages,
                    status=SuccessMessageStatus(),
                    execution_time=execution_time
                )
                
                for middleware in reversed(self.middlewares):  # 后置中间件反向执行
                    result = await middleware.after_request(after_options)
                    if not result.success:
                        logger.warning(f"After-request middleware failed: {result.error}")
                    
                    # 合并元数据
                    context.metadata.update(result.metadata)
                
                return MiddlewareResult(success=True, metadata=context.metadata)
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # 执行错误处理
                for middleware in self.middlewares:
                    try:
                        await middleware.on_error(e, context)
                    except Exception as middleware_error:
                        logger.error(f"Error in middleware error handler: {middleware_error}")
                
                return MiddlewareResult(
                    success=False,
                    error=str(e),
                    metadata=context.metadata
                )
                
        except Exception as e:
            logger.error(f"Error in middleware chain: {e}")
            return MiddlewareResult(success=False, error=str(e))
    
    def create_output_messages_future(self, thread_id: str) -> asyncio.Future[List[Message]]:
        """
        创建输出消息 Future（类似 TypeScript 版本）
        
        Args:
            thread_id: 线程ID
            
        Returns:
            输出消息的 Future
        """
        future = asyncio.Future()
        self.output_message_futures[thread_id] = future
        return future
    
    def resolve_output_messages(self, thread_id: str, messages: List[Message]):
        """
        解析输出消息 Future
        
        Args:
            thread_id: 线程ID
            messages: 输出消息列表
        """
        if thread_id in self.output_message_futures:
            future = self.output_message_futures[thread_id]
            if not future.done():
                future.set_result(messages)
            del self.output_message_futures[thread_id]
    
    def reject_output_messages(self, thread_id: str, error: Exception):
        """
        拒绝输出消息 Future
        
        Args:
            thread_id: 线程ID
            error: 错误信息
        """
        if thread_id in self.output_message_futures:
            future = self.output_message_futures[thread_id]
            if not future.done():
                future.set_exception(error)
            del self.output_message_futures[thread_id]


class MiddlewareBuilder:
    """中间件构建器"""
    
    def __init__(self):
        self.chain = EnhancedMiddlewareChain()
    
    def add_logging(self, level: int = logging.INFO):
        """添加日志中间件"""
        self.chain.add_middleware(LoggingMiddleware(level))
        return self
    
    def add_metrics(self):
        """添加指标中间件"""
        self.chain.add_middleware(MetricsMiddleware())
        return self
    
    def add_authentication(self, api_keys: Optional[List[str]] = None):
        """添加认证中间件"""
        self.chain.add_middleware(AuthenticationMiddleware(api_keys))
        return self
    
    def add_rate_limit(self, max_requests_per_minute: int = 60):
        """添加限流中间件"""
        self.chain.add_middleware(RateLimitMiddleware(max_requests_per_minute))
        return self
    
    def add_custom(self, middleware: BaseMiddleware):
        """添加自定义中间件"""
        self.chain.add_middleware(middleware)
        return self
    
    def build(self) -> EnhancedMiddlewareChain:
        """构建中间件链"""
        return self.chain


# 便捷函数
def create_default_middleware_chain() -> EnhancedMiddlewareChain:
    """创建默认的中间件链"""
    return (MiddlewareBuilder()
            .add_logging()
            .add_metrics()
            .build())


def create_production_middleware_chain(api_keys: Optional[List[str]] = None) -> EnhancedMiddlewareChain:
    """创建生产环境的中间件链"""
    return (MiddlewareBuilder()
            .add_authentication(api_keys)
            .add_rate_limit(max_requests_per_minute=100)
            .add_logging(level=logging.WARNING)
            .add_metrics()
            .build()) 