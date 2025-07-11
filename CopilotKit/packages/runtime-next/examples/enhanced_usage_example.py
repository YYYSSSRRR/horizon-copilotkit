"""
增强的 CopilotKit Runtime 使用示例

展示了如何使用增强功能，包括：
- 增强的事件系统
- 复杂的中间件管道
- AsyncRepeater 流式处理
- 状态管理和错误处理
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

# 导入增强的运行时组件
from copilotkit_runtime import (
    # 核心运行时
    EnhancedCopilotRuntime,
    create_enhanced_runtime,
    
    # 适配器
    DeepSeekAdapter,
    OpenAIAdapter,
    
    # 动作和消息类型
    Action,
    Parameter,
    ParameterType,
    TextMessage,
    MessageRole,
    
    # 中间件
    BaseMiddleware,
    MiddlewareBuilder,
    LoggingMiddleware,
    MetricsMiddleware,
    create_production_middleware_chain,
    
    # 事件系统
    AsyncRepeater,
    EnhancedRuntimeEventSource,
    
    # FastAPI 集成
    CopilotRuntimeServer,
    
    # 请求/响应类型
    CopilotRuntimeRequest,
    RequestContext
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 示例1: 自定义中间件
class CustomAnalyticsMiddleware(BaseMiddleware):
    """自定义分析中间件"""
    
    def __init__(self):
        self.analytics_data = []
    
    async def before_request(self, options) -> Any:
        """请求前分析"""
        analytics_event = {
            "type": "request_started",
            "thread_id": options.context.thread_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(options.input_messages),
            "user_properties": options.context.properties
        }
        self.analytics_data.append(analytics_event)
        
        logger.info(f"📊 Analytics: Request started for thread {options.context.thread_id}")
        return {"success": True}
    
    async def after_request(self, options) -> Any:
        """请求后分析"""
        analytics_event = {
            "type": "request_completed",
            "thread_id": options.context.thread_id,
            "timestamp": datetime.now().isoformat(),
            "output_message_count": len(options.output_messages),
            "execution_time": options.execution_time,
            "status": options.status.code
        }
        self.analytics_data.append(analytics_event)
        
        logger.info(f"📊 Analytics: Request completed in {options.execution_time:.3f}s")
        return {"success": True}
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        total_requests = len([e for e in self.analytics_data if e["type"] == "request_started"])
        completed_requests = len([e for e in self.analytics_data if e["type"] == "request_completed"])
        
        execution_times = [
            e["execution_time"] for e in self.analytics_data 
            if e["type"] == "request_completed"
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "average_execution_time": avg_execution_time,
            "success_rate": completed_requests / total_requests if total_requests > 0 else 0
        }


# 示例2: 动作定义
async def get_weather(location: str, units: str = "celsius") -> str:
    """获取天气信息的示例动作"""
    # 模拟API调用
    await asyncio.sleep(0.1)
    
    weather_data = {
        "beijing": {"celsius": "22°C 晴朗", "fahrenheit": "72°F Sunny"},
        "shanghai": {"celsius": "25°C 多云", "fahrenheit": "77°F Cloudy"},
        "guangzhou": {"celsius": "28°C 小雨", "fahrenheit": "82°F Light Rain"}
    }
    
    location_lower = location.lower()
    if location_lower in weather_data:
        return weather_data[location_lower].get(units, weather_data[location_lower]["celsius"])
    else:
        return f"{location}的天气信息暂时不可用"


async def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件的示例动作"""
    # 模拟邮件发送
    await asyncio.sleep(0.2)
    
    logger.info(f"📧 Sending email to {to}: {subject}")
    return f"邮件已成功发送到 {to}"


async def search_database(query: str, table: str = "users") -> List[Dict[str, Any]]:
    """数据库搜索示例动作"""
    # 模拟数据库查询
    await asyncio.sleep(0.15)
    
    mock_data = {
        "users": [
            {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
            {"id": 2, "name": "李四", "email": "lisi@example.com"}
        ],
        "products": [
            {"id": 1, "name": "iPhone 15", "price": 6999},
            {"id": 2, "name": "MacBook Pro", "price": 12999}
        ]
    }
    
    return mock_data.get(table, [])


# 示例3: 动态动作生成
def create_actions_for_context(context: Dict[str, Any]) -> List[Action]:
    """根据上下文动态创建动作"""
    base_actions = [
        Action(
            name="get_weather",
            description="获取指定地点的天气信息",
            parameters=[
                Parameter(
                    name="location",
                    type=ParameterType.STRING,
                    description="地点名称",
                    required=True
                ),
                Parameter(
                    name="units",
                    type=ParameterType.STRING,
                    description="温度单位 (celsius/fahrenheit)",
                    required=False
                )
            ],
            handler=get_weather
        )
    ]
    
    # 根据用户权限添加更多动作
    user_role = context.get("properties", {}).get("user_role", "guest")
    
    if user_role in ["admin", "user"]:
        base_actions.append(Action(
            name="send_email",
            description="发送邮件",
            parameters=[
                Parameter(
                    name="to",
                    type=ParameterType.STRING,
                    description="收件人邮箱",
                    required=True
                ),
                Parameter(
                    name="subject",
                    type=ParameterType.STRING,
                    description="邮件主题",
                    required=True
                ),
                Parameter(
                    name="body",
                    type=ParameterType.STRING,
                    description="邮件内容",
                    required=True
                )
            ],
            handler=send_email
        ))
    
    if user_role == "admin":
        base_actions.append(Action(
            name="search_database",
            description="搜索数据库",
            parameters=[
                Parameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="搜索查询",
                    required=True
                ),
                Parameter(
                    name="table",
                    type=ParameterType.STRING,
                    description="数据表名称",
                    required=False
                )
            ],
            handler=search_database
        ))
    
    return base_actions


# 示例4: 增强运行时使用
async def example_enhanced_runtime():
    """增强运行时使用示例"""
    
    # 创建自定义中间件链
    analytics_middleware = CustomAnalyticsMiddleware()
    middleware_chain = (MiddlewareBuilder()
                       .add_logging(level=logging.INFO)
                       .add_metrics()
                       .add_custom(analytics_middleware)
                       .build())
    
    # 创建适配器
    adapter = DeepSeekAdapter(
        api_key="your-deepseek-key",  # 实际使用时替换为真实密钥
        model="deepseek-chat"
    )
    
    # 创建增强运行时
    runtime = EnhancedCopilotRuntime(
        actions=create_actions_for_context,  # 动态动作生成
        middleware_chain=middleware_chain
    )
    
    # 创建测试消息
    messages = [
        TextMessage(
            id="msg-1",
            content="请帮我查询北京的天气",
            role=MessageRole.USER
        )
    ]
    
    # 创建请求
    request = CopilotRuntimeRequest(
        service_adapter=adapter,
        messages=messages,
        thread_id="test-thread-1",
        context=RequestContext(
            properties={
                "user_role": "admin",
                "user_id": "user123"
            }
        )
    )
    
    try:
        # 处理请求
        logger.info("🚀 开始处理增强运行时请求...")
        response = await runtime.process_runtime_request(request)
        
        # 创建消息流
        logger.info("📡 创建消息流...")
        message_stream = await response.create_message_stream()
        await message_stream.start()
        
        # 处理流式消息
        logger.info("📝 处理流式消息...")
        async for message in message_stream:
            logger.info(f"收到消息: {message}")
        
        # 获取运行时指标
        logger.info("📊 获取运行时指标...")
        metrics = runtime.get_metrics()
        logger.info(f"运行时指标: {metrics}")
        
        # 获取分析数据
        analytics_summary = analytics_middleware.get_analytics_summary()
        logger.info(f"分析摘要: {analytics_summary}")
        
        logger.info("✅ 增强运行时示例完成")
        
    except Exception as e:
        logger.error(f"❌ 错误: {e}")


# 示例5: 流式处理演示
async def example_async_repeater():
    """AsyncRepeater 使用示例"""
    
    async def number_generator(push_item, stop_iteration):
        """数字生成器"""
        try:
            for i in range(10):
                await push_item(f"数字: {i}")
                await asyncio.sleep(0.1)  # 模拟异步操作
        finally:
            stop_iteration()
    
    # 创建 AsyncRepeater
    repeater = AsyncRepeater(number_generator)
    await repeater.start()
    
    # 消费流
    logger.info("🔢 AsyncRepeater 示例:")
    async for item in repeater:
        logger.info(f"  {item}")


# 示例6: FastAPI 集成
def create_enhanced_server():
    """创建增强的 FastAPI 服务器"""
    
    # 创建适配器
    adapter = DeepSeekAdapter(
        api_key="your-deepseek-key",
        model="deepseek-chat"
    )
    
    # 创建增强运行时
    runtime = create_enhanced_runtime(
        actions=create_actions_for_context,
        use_default_middleware=True,
        api_keys=["test-api-key-1", "test-api-key-2"]  # 生产环境密钥
    )
    
    # 创建服务器
    server = CopilotRuntimeServer(
        runtime=runtime,
        service_adapter=adapter,
        title="Enhanced CopilotKit Runtime",
        version="1.0.0-enhanced",
        cors_origins=["http://localhost:3000", "https://yourdomain.com"]
    )
    
    return server


# 主函数
async def main():
    """主函数 - 运行所有示例"""
    
    logger.info("🎯 开始运行增强 CopilotKit Runtime 示例")
    
    # 示例1: AsyncRepeater
    await example_async_repeater()
    
    # 示例2: 增强运行时
    await example_enhanced_runtime()
    
    # 示例3: 服务器创建（不运行）
    logger.info("🌐 创建增强服务器...")
    server = create_enhanced_server()
    logger.info(f"服务器创建完成: {server.app.title}")
    
    logger.info("🎉 所有示例运行完成!")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
    
    # 如果要运行 FastAPI 服务器，取消注释以下代码：
    # server = create_enhanced_server()
    # server.run(host="0.0.0.0", port=8000) 