"""
Copilot Resolver

对标TypeScript的copilot.resolver.ts，使用RxPY实现流式处理
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from datetime import datetime

import reactivex as rx
from reactivex import operators as ops
from reactivex.subject import ReplaySubject

from ..types.runtime import CopilotRuntimeRequest, CopilotResponse
from ..types.messages import (
    Message,
    TextMessage,
    ActionExecutionMessage,
    ResultMessage,
    MessageRole,
    MessageType
)
from ..types.events import RuntimeEvent, RuntimeEventTypes
from ..types.actions import ActionInput
from ..types.status import (
    SuccessMessageStatus,
    FailedMessageStatus,
    MessageStatusCode
)
from ..streaming import StreamingResponse, MessageStreamer
from ..utils import random_id

logger = logging.getLogger(__name__)


class CopilotResolver:
    """
    Copilot解析器
    
    对标TypeScript的CopilotResolver类，负责处理Copilot请求和响应流
    """
    
    def __init__(self, runtime):
        self.runtime = runtime
        self._active_streams = {}
    
    async def hello(self) -> str:
        """健康检查端点"""
        return "Hello from CopilotKit Python Runtime!"
    
    async def available_agents(self) -> Dict[str, Any]:
        """获取可用代理列表"""
        # TODO: 实现代理发现逻辑
        return {"agents": []}
    
    async def generate_copilot_response(
        self,
        data: Dict[str, Any],
        properties: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成Copilot响应
        
        对标TypeScript的generateCopilotResponse方法
        使用异步生成器实现流式响应
        """
        # 解析请求数据
        request = self._parse_request_data(data)
        thread_id = request.thread_id or random_id()
        run_id = request.run_id or random_id()
        
        logger.info(f"🚀 [CopilotResolver] 生成响应: thread_id={thread_id}, "
                   f"messages={len(request.messages)}, actions={len(request.actions)}")
        
        # 创建响应状态主题
        response_status_subject = ReplaySubject(buffer_size=1)
        interrupt_streaming_subject = ReplaySubject(buffer_size=1)
        
        # 创建消息流处理器
        message_streamer = MessageStreamer()
        
        try:
            # 开始处理请求
            response_status_subject.on_next({
                "type": "processing",
                "message": "开始处理请求"
            })
            
            # 处理消息流
            async for stream_item in self._process_message_stream(
                request, 
                message_streamer,
                thread_id,
                run_id
            ):
                yield stream_item
            
            # 完成处理
            response_status_subject.on_next({
                "type": "success", 
                "message": "请求处理完成"
            })
            
            logger.info(f"✅ [CopilotResolver] 响应完成: thread_id={thread_id}")
            
        except Exception as e:
            logger.error(f"❌ [CopilotResolver] 处理失败: {e}")
            
            # 发送错误状态
            response_status_subject.on_next({
                "type": "error",
                "message": str(e)
            })
            
            # 发送错误消息
            error_message = {
                "id": random_id(),
                "thread_id": thread_id,
                "run_id": run_id,
                "messages": [{
                    "id": random_id(),
                    "role": MessageRole.ASSISTANT.value,
                    "content": f"抱歉，处理请求时遇到错误: {str(e)}",
                    "type": MessageType.TEXT_MESSAGE.value,
                    "created_at": datetime.utcnow().isoformat(),
                    "status": {
                        "code": MessageStatusCode.FAILED.value,
                        "reason": str(e)
                    }
                }],
                "status": {
                    "code": MessageStatusCode.FAILED.value,
                    "reason": str(e)
                }
            }
            yield error_message
        
        finally:
            # 清理资源
            response_status_subject.on_completed()
            interrupt_streaming_subject.on_completed()
    
    def _parse_request_data(self, data: Dict[str, Any]) -> CopilotRuntimeRequest:
        """解析请求数据"""
        # 解析消息
        messages = []
        for msg_data in data.get("messages", []):
            # 根据消息类型创建对应的消息对象
            if msg_data.get("textMessage"):
                text_msg = msg_data["textMessage"]
                message = TextMessage(
                    id=msg_data.get("id", random_id()),
                    role=MessageRole(text_msg["role"]),
                    content=text_msg["content"],
                    type=MessageType.TEXT_MESSAGE,
                    parent_message_id=text_msg.get("parentMessageId")
                )
            elif msg_data.get("actionExecutionMessage"):
                action_msg = msg_data["actionExecutionMessage"]
                message = ActionExecutionMessage(
                    id=msg_data.get("id", random_id()),
                    name=action_msg["name"],
                    arguments=action_msg.get("arguments", {}),
                    type=MessageType.ACTION_EXECUTION_MESSAGE,
                    parent_message_id=action_msg.get("parentMessageId")
                )
            elif msg_data.get("resultMessage"):
                result_msg = msg_data["resultMessage"]
                message = ResultMessage(
                    id=msg_data.get("id", random_id()),
                    action_execution_id=result_msg["actionExecutionId"],
                    action_name=result_msg["actionName"],
                    result=result_msg["result"],
                    type=MessageType.RESULT_MESSAGE
                )
            else:
                # 跳过不支持的消息类型
                continue
            
            messages.append(message)
        
        # 解析动作
        actions = []
        frontend_actions = data.get("frontend", {}).get("actions", [])
        for action_data in frontend_actions:
            action = ActionInput(
                name=action_data["name"],
                description=action_data["description"],
                parameters=action_data.get("parameters", [])
            )
            actions.append(action)
        
        # 创建请求对象
        return CopilotRuntimeRequest(
            messages=messages,
            actions=actions,
            thread_id=data.get("threadId"),
            run_id=data.get("runId"),
            forwarded_parameters=data.get("forwardedParameters"),
            extensions=data.get("extensions"),
            agent_session=data.get("agentSession"),
            agent_states=data.get("agentStates")
        )
    
    async def _process_message_stream(
        self,
        request: CopilotRuntimeRequest,
        message_streamer: MessageStreamer,
        thread_id: str,
        run_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理消息流
        
        对标TypeScript的messages Repeater逻辑
        """
        logger.debug(f"🔄 [CopilotResolver] 开始消息流处理")
        
        # 使用服务适配器处理请求
        service_adapter = self.runtime.get_service_adapter()
        if not service_adapter:
            raise Exception("未配置服务适配器")
        
        # 创建适配器请求
        from ..types.adapters import AdapterRequest
        adapter_request = AdapterRequest(
            messages=request.messages,
            actions=request.actions,
            thread_id=thread_id,
            run_id=run_id,
            forwarded_parameters=request.forwarded_parameters,
            extensions=request.extensions
        )
        
        # 处理请求并获取响应
        try:
            adapter_response = await service_adapter.process(adapter_request)
            
            # 处理响应消息
            if adapter_response.messages:
                for message in adapter_response.messages:
                    # 转换消息为流格式
                    stream_message = self._convert_message_to_stream_format(
                        message, thread_id, run_id
                    )
                    yield stream_message
            
            elif adapter_response.message:
                # 单个消息响应
                stream_message = self._convert_message_to_stream_format(
                    adapter_response.message, thread_id, run_id
                )
                yield stream_message
        
        except Exception as e:
            logger.error(f"❌ [CopilotResolver] 适配器处理失败: {e}")
            raise
    
    def _convert_message_to_stream_format(
        self, 
        message: Message, 
        thread_id: str, 
        run_id: str
    ) -> Dict[str, Any]:
        """将消息转换为流格式"""
        
        # 创建状态对象
        if message.is_text_message():
            status = {
                "code": MessageStatusCode.SUCCESS.value
            }
        else:
            status = {
                "code": MessageStatusCode.SUCCESS.value
            }
        
        # 基础消息格式
        base_message = {
            "id": message.id,
            "created_at": message.created_at.isoformat(),
            "status": status
        }
        
        # 根据消息类型添加特定字段
        if message.is_text_message():
            base_message.update({
                "role": message.role.value,
                "content": self._create_content_repeater(message.content),
                "parentMessageId": message.parent_message_id
            })
        
        elif message.is_action_execution_message():
            base_message.update({
                "name": message.name,
                "arguments": message.arguments,
                "parentMessageId": message.parent_message_id
            })
        
        elif message.is_result_message():
            base_message.update({
                "actionExecutionId": message.action_execution_id,
                "actionName": message.action_name,
                "result": message.result
            })
        
        # 包装在响应结构中
        return {
            "thread_id": thread_id,
            "run_id": run_id,
            "messages": [base_message],
            "status": {
                "code": MessageStatusCode.SUCCESS.value
            }
        }
    
    def _create_content_repeater(self, content: str) -> Dict[str, Any]:
        """
        创建内容重复器，模拟TypeScript的嵌套Repeater
        
        在实际实现中，这里会返回一个流式内容生成器
        为了简化，我们直接返回完整内容
        """
        return {
            "type": "text_content",
            "content": content,
            "streaming": False  # 标记为非流式内容
        }
    
    async def _create_streaming_content(self, content: str) -> AsyncGenerator[str, None]:
        """创建流式内容生成器"""
        # 模拟流式输出，将内容分块发送
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)  # 模拟延迟
    
    def cleanup_stream(self, thread_id: str):
        """清理流资源"""
        if thread_id in self._active_streams:
            del self._active_streams[thread_id]
            logger.debug(f"🧹 [CopilotResolver] 清理流: {thread_id}")


class CopilotGraphQLResolver:
    """
    GraphQL兼容的Copilot解析器
    
    提供GraphQL风格的接口，但内部使用REST/JSON处理
    """
    
    def __init__(self, copilot_resolver: CopilotResolver):
        self.copilot_resolver = copilot_resolver
    
    async def query_hello(self) -> str:
        """Query: hello"""
        return await self.copilot_resolver.hello()
    
    async def query_available_agents(self) -> Dict[str, Any]:
        """Query: availableAgents"""
        return await self.copilot_resolver.available_agents()
    
    async def mutation_generate_copilot_response(
        self,
        data: Dict[str, Any],
        properties: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mutation: generateCopilotResponse"""
        async for response in self.copilot_resolver.generate_copilot_response(data, properties):
            yield response 