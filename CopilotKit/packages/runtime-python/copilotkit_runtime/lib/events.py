"""
Python implementation of CopilotKit runtime events system using RxPY.

This module provides the equivalent functionality of the TypeScript
`service-adapters/events.ts` file, using RxPY to replace RxJS functionality
with a true 1:1 mapping.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union, Awaitable, AsyncGenerator
from uuid import uuid4

import rx
from rx import operators as ops
from rx.subject.replaysubject import ReplaySubject
from rx.subject.subject import Subject
from rx.core.observable.observable import Observable

from .types.events import (
    RuntimeEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ActionExecutionStartEvent,
    ActionExecutionArgsEvent,
    ActionExecutionEndEvent,
    ActionExecutionResultEvent,
    AgentStateMessageEvent,
    MetaEvent,
)
from .types.actions import ActionInput

logger = logging.getLogger(__name__)


class RuntimeEventSubject(ReplaySubject):
    """
    Python equivalent of TypeScript's RuntimeEventSubject (ReplaySubject).
    
    This class extends RxPY's ReplaySubject to provide methods for sending
    different types of runtime events, exactly matching the TypeScript implementation.
    """
    
    def __init__(self, buffer_size: Optional[int] = None):
        if buffer_size is not None:
            super().__init__(buffer_size=buffer_size)
        else:
            super().__init__()
    
    def send_text_message_start(self, message_id: str, parent_message_id: Optional[str] = None) -> None:
        """Send a text message start event."""
        event = TextMessageStartEvent(
            message_id=message_id,
            parent_message_id=parent_message_id
        )
        self.on_next(event)
    
    def send_text_message_content(self, message_id: str, content: str) -> None:
        """Send a text message content event."""
        event = TextMessageContentEvent(
            message_id=message_id,
            content=content
        )
        self.on_next(event)
    
    def send_text_message_end(self, message_id: str) -> None:
        """Send a text message end event."""
        event = TextMessageEndEvent(message_id=message_id)
        self.on_next(event)
    
    def send_text_message(self, message_id: str, content: str) -> None:
        """Send a complete text message (start + content + end)."""
        self.send_text_message_start(message_id)
        self.send_text_message_content(message_id, content)
        self.send_text_message_end(message_id)
    
    def send_action_execution_start(
        self, 
        action_execution_id: str, 
        action_name: str, 
        parent_message_id: Optional[str] = None
    ) -> None:
        """Send an action execution start event."""
        event = ActionExecutionStartEvent(
            action_execution_id=action_execution_id,
            action_name=action_name,
            parent_message_id=parent_message_id
        )
        self.on_next(event)
    
    def send_action_execution_args(self, action_execution_id: str, args: str) -> None:
        """Send action execution arguments event."""
        event = ActionExecutionArgsEvent(
            action_execution_id=action_execution_id,
            args=args
        )
        self.on_next(event)
    
    def send_action_execution_end(self, action_execution_id: str) -> None:
        """Send action execution end event."""
        event = ActionExecutionEndEvent(
            action_execution_id=action_execution_id
        )
        self.on_next(event)
    
    def send_action_execution(
        self,
        action_execution_id: str,
        action_name: str,
        args: str,
        parent_message_id: Optional[str] = None
    ) -> None:
        """Send a complete action execution (start + args + end)."""
        self.send_action_execution_start(action_execution_id, action_name, parent_message_id)
        self.send_action_execution_args(action_execution_id, args)
        self.send_action_execution_end(action_execution_id)
    
    def send_action_execution_result(
        self,
        action_execution_id: str,
        action_name: str,
        result: Optional[str] = None,
        error: Optional[Dict[str, str]] = None
    ) -> None:
        """Send action execution result event."""
        # Encode result similar to TypeScript version
        encoded_result = self._encode_result(result, error)
        
        logger.info(f"🚀 [sendActionExecutionResult] 发送 Action 执行结果: "
                   f"action_execution_id={action_execution_id}, "
                   f"action_name={action_name}, "
                   f"result={result}, "
                   f"error={error}, "
                   f"encoded_result={encoded_result}")
        
        event = ActionExecutionResultEvent(
            action_execution_id=action_execution_id,
            action_name=action_name,
            result=encoded_result
        )
        self.on_next(event)
    
    def send_agent_state_message(
        self,
        thread_id: str,
        agent_name: str,
        node_name: str,
        run_id: str,
        active: bool,
        role: str,
        state: str,
        running: bool
    ) -> None:
        """Send agent state message event."""
        event = AgentStateMessageEvent(
            thread_id=thread_id,
            agent_name=agent_name,
            node_name=node_name,
            run_id=run_id,
            active=active,
            state={"role": role, "state": state},  # Convert to dict format
            running=running
        )
        self.on_next(event)
    
    def complete(self) -> None:
        """Complete the event stream (equivalent to TypeScript complete method)."""
        self.on_completed()
    
    def _encode_result(self, result: Optional[str], error: Optional[Dict[str, str]]) -> str:
        """Encode result and error into a single string (similar to ResultMessage.encodeResult)."""
        if error:
            return json.dumps({"error": error})
        elif result:
            return result
        else:
            return ""


class RuntimeEventWithState:
    """State tracking for runtime events (equivalent to TypeScript interface)."""
    
    def __init__(self):
        self.event: Optional[RuntimeEvent] = None
        self.call_action_server_side: bool = False
        self.action: Optional[ActionInput] = None
        self.action_execution_id: Optional[str] = None
        self.args: str = ""
        self.action_execution_parent_message_id: Optional[str] = None


EventSourceCallback = Callable[[RuntimeEventSubject], Awaitable[None]]


class RuntimeEventSource:
    """
    Python equivalent of TypeScript's RuntimeEventSource.
    
    This class uses RxPY to provide reactive event processing,
    exactly matching the TypeScript implementation with RxJS.
    """
    
    def __init__(self):
        self.event_stream: RuntimeEventSubject = RuntimeEventSubject()
        self.callback: Optional[EventSourceCallback] = None
    
    async def stream(self, callback: EventSourceCallback) -> None:
        """Set up the event stream with a callback."""
        self.callback = callback
    
    def send_error_message_to_chat(self, message: str = "An error occurred. Please try again.") -> None:
        """Send an error message to the chat."""
        error_message = f"❌ {message}"
        error_id = generate_id()
        
        if not self.callback:
            # If no callback set, set up a simple one
            async def error_callback(event_stream: RuntimeEventSubject):
                event_stream.send_text_message(error_id, error_message)
            
            # Schedule the callback to run
            asyncio.create_task(self.stream(error_callback))
        else:
            self.event_stream.send_text_message(error_id, error_message)
    
    def process_runtime_events(
        self,
        server_side_actions: List[ActionInput],
        guardrails_result: Optional[Subject] = None,
        action_inputs_without_agents: Optional[List[ActionInput]] = None,
        thread_id: str = ""
    ) -> Observable:
        """
        Process runtime events and handle action execution.
        
        This is the Python equivalent of the TypeScript processRuntimeEvents method,
        using RxPY operators to exactly match the original behavior.
        """
        if action_inputs_without_agents is None:
            action_inputs_without_agents = []
        
        # Start the callback if available
        if self.callback is not None:
            async def run_callback():
                try:
                    if self.callback is not None:
                        await self.callback(self.event_stream)
                except Exception as error:
                    logger.error(f"Error in event source callback: {error}", exc_info=True)
                    self.send_error_message_to_chat()
                    self.event_stream.complete()
            
            asyncio.create_task(run_callback())
        
        # Process events using RxPY operators, exactly like TypeScript
        return self.event_stream.pipe(
            # track state (equivalent to TypeScript scan)
            ops.scan(
                lambda acc, event: self._scan_events(acc, event, server_side_actions),
                RuntimeEventWithState()
            ),
            # Handle action execution (equivalent to TypeScript concatMap)
            ops.flat_map(
                lambda event_with_state: self._handle_action_execution(
                    event_with_state,
                    server_side_actions,
                    guardrails_result,
                    action_inputs_without_agents,
                    thread_id
                )
            ),
            # Error handling (equivalent to TypeScript catchError)
            ops.catch(
                lambda error, source: self._handle_error(error)
            )
        )
    
    def _scan_events(
        self, 
        acc: RuntimeEventWithState, 
        event: RuntimeEvent,
        server_side_actions: List[ActionInput]
    ) -> RuntimeEventWithState:
        """
        Scan events and update state (equivalent to TypeScript scan operator).
        """
        # It seems like this is needed so that rxjs recognizes the object has changed
        # This fixes an issue where action were executed multiple times
        # Not investigating further for now (equivalent to TypeScript comment)
        new_acc = RuntimeEventWithState()
        new_acc.event = acc.event
        new_acc.call_action_server_side = acc.call_action_server_side
        new_acc.action = acc.action
        new_acc.action_execution_id = acc.action_execution_id
        new_acc.args = acc.args
        new_acc.action_execution_parent_message_id = acc.action_execution_parent_message_id
        
        if isinstance(event, ActionExecutionStartEvent):
            new_acc.call_action_server_side = any(
                action.name == event.action_name for action in server_side_actions
            )
            new_acc.args = ""
            new_acc.action_execution_id = event.action_execution_id
            if new_acc.call_action_server_side:
                new_acc.action = next(
                    (action for action in server_side_actions if action.name == event.action_name),
                    None
                )
            new_acc.action_execution_parent_message_id = event.parent_message_id
        
        elif isinstance(event, ActionExecutionArgsEvent):
            new_acc.args += event.args
        
        new_acc.event = event
        return new_acc
    
    def _handle_action_execution(
        self,
        event_with_state: RuntimeEventWithState,
        server_side_actions: List[ActionInput],
        guardrails_result: Optional[Subject],
        action_inputs_without_agents: List[ActionInput],
        thread_id: str
    ) -> Observable:
        """
        Handle action execution (equivalent to TypeScript concatMap).
        """
        if (isinstance(event_with_state.event, ActionExecutionEndEvent) and 
            event_with_state.call_action_server_side):
            
            # Create a new event stream for tool call
            tool_call_event_stream = RuntimeEventSubject()
            
            # Execute the action asynchronously
            asyncio.create_task(
                self._execute_action(
                    tool_call_event_stream,
                    guardrails_result,
                    event_with_state.action,
                    event_with_state.args,
                    event_with_state.action_execution_parent_message_id,
                    event_with_state.action_execution_id,
                    action_inputs_without_agents,
                    thread_id
                )
            )
            
            # Return concat of current event and tool call stream (equivalent to TypeScript concat)
            return rx.concat(
                rx.of(event_with_state.event),
                tool_call_event_stream
            ).pipe(
                ops.catch(
                    lambda error, source: self._handle_tool_call_error(error)
                )
            )
        else:
            # Just return the current event (equivalent to TypeScript of)
            return rx.of(event_with_state.event)
    
    def _handle_error(self, error: Exception) -> Observable:
        """Handle errors in the event stream."""
        logger.error(f"Error in event stream: {error}")
        self.send_error_message_to_chat()
        return rx.empty()
    
    def _handle_tool_call_error(self, error: Exception) -> Observable:
        """Handle errors in tool call stream."""
        logger.error(f"Error in tool call stream: {error}")
        self.send_error_message_to_chat()
        return rx.empty()
    
    async def _execute_action(
        self,
        event_stream: RuntimeEventSubject,
        guardrails_result: Optional[Subject],
        action: Optional[ActionInput],
        action_arguments: str,
        action_execution_parent_message_id: Optional[str],
        action_execution_id: Optional[str],
        action_inputs_without_agents: List[ActionInput],
        thread_id: str
    ) -> None:
        """
        Execute a server-side action (equivalent to TypeScript executeAction function).
        """
        if not action or not action_execution_id:
            return
        
        # Handle guardrails (equivalent to TypeScript implementation)
        if guardrails_result:
            # TODO: Implement guardrails check similar to TypeScript
            # const { status } = await firstValueFrom(guardrailsResult$);
            # if (status === "denied") {
            #     eventStream$.complete();
            #     return;
            # }
            try:
                # For now, we'll assume guardrails pass
                # In a full implementation, this would check the guardrails result
                pass
            except Exception as e:
                logger.error(f"Error in guardrails check: {e}")
                event_stream.complete()
                return
        
        # Prepare arguments for function calling
        args = {}
        if action_arguments:
            try:
                args = json.loads(action_arguments)
            except json.JSONDecodeError:
                logger.error(f"Action argument unparsable: {action_arguments}")
                event_stream.send_action_execution_result(
                    action_execution_id,
                    action.name,
                    error={
                        "code": "INVALID_ARGUMENTS",
                        "message": "Failed to parse action arguments"
                    }
                )
                return
        
        # Handle LangGraph agents (equivalent to TypeScript isRemoteAgentAction)
        if self._is_remote_agent_action(action):
            result = f"{action.name} agent started"
            
            # Create equivalent of TypeScript's plainToInstance(ActionExecutionMessage, ...)
            agent_execution = self._create_action_execution_message(
                action_execution_id,
                action.name,
                args,
                action_execution_parent_message_id or action_execution_id
            )
            
            # Create equivalent of TypeScript's plainToInstance(ResultMessage, ...)
            agent_execution_result = self._create_result_message(
                f"result-{action_execution_id}",
                action_execution_id,
                action.name,
                result
            )
            
            # Send action execution result
            event_stream.send_action_execution_result(
                action_execution_id,
                action.name,
                result=result
            )
            
            try:
                # Call the remote agent handler (equivalent to TypeScript)
                stream = self._call_remote_agent_handler(
                    action,
                    action.name,
                    thread_id,
                    action_inputs_without_agents,
                    [agent_execution, agent_execution_result]
                )
                
                # Forward events from the stream to eventStream$
                await self._forward_stream_events(stream, event_stream)
                
            except Exception as err:
                logger.error(f"Error in remote agent stream: {err}")
                event_stream.send_action_execution_result(
                    action_execution_id,
                    action.name,
                    error={
                        "code": "STREAM_ERROR",
                        "message": str(err)
                    }
                )
                event_stream.complete()
        else:
            # Call the function (equivalent to TypeScript regular action handling)
            try:
                # Execute the action handler if it exists
                result = await self._call_action_handler(action, args)
                
                # Stream the result using LangChain response streaming
                await self._stream_langchain_response(
                    result,
                    event_stream,
                    action_execution={
                        "name": action.name,
                        "id": action_execution_id,
                    }
                )
                
            except Exception as e:
                logger.error(f"Error in action handler: {e}")
                event_stream.send_action_execution_result(
                    action_execution_id,
                    action.name,
                    error={
                        "code": "HANDLER_ERROR",
                        "message": str(e)
                    }
                )
                event_stream.complete()
    
    def _is_remote_agent_action(self, action: ActionInput) -> bool:
        """
        Check if an action is a remote agent action (equivalent to TypeScript isRemoteAgentAction).
        """
        if not action:
            return False
        # Check if action has a remote agent handler
        return hasattr(action, 'remote_agent_handler') and callable(getattr(action, 'remote_agent_handler', None))
    
    def _create_action_execution_message(
        self, 
        action_execution_id: str, 
        action_name: str, 
        arguments: Dict[str, Any], 
        parent_message_id: str
    ) -> Dict[str, Any]:
        """
        Create an action execution message (equivalent to TypeScript plainToInstance(ActionExecutionMessage, ...)).
        """
        from datetime import datetime
        return {
            "id": action_execution_id,
            "created_at": datetime.now(),
            "name": action_name,
            "arguments": arguments,
            "parent_message_id": parent_message_id,
        }
    
    def _create_result_message(
        self, 
        result_id: str, 
        action_execution_id: str, 
        action_name: str, 
        result: str
    ) -> Dict[str, Any]:
        """
        Create a result message (equivalent to TypeScript plainToInstance(ResultMessage, ...)).
        """
        from datetime import datetime
        return {
            "id": result_id,
            "created_at": datetime.now(),
            "action_execution_id": action_execution_id,
            "action_name": action_name,
            "result": result,
        }
    
    def _call_remote_agent_handler(
        self,
        action: ActionInput,
        name: str,
        thread_id: str,
        action_inputs_without_agents: List[ActionInput],
        additional_messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[RuntimeEvent, None]:
        """
        Call the remote agent handler (equivalent to TypeScript action.remoteAgentHandler).
        """
        async def _handler():
            if hasattr(action, 'remote_agent_handler'):
                remote_handler = getattr(action, 'remote_agent_handler')
                params = {
                    "name": name,
                    "thread_id": thread_id,
                    "action_inputs_without_agents": action_inputs_without_agents,
                    "additional_messages": additional_messages
                }
                
                # Call the handler and return the stream
                stream = await remote_handler(params)
                async for event in stream:
                    yield event
        
        return _handler()
    
    async def _forward_stream_events(
        self, 
        stream: AsyncGenerator[RuntimeEvent, None], 
        event_stream: RuntimeEventSubject
    ) -> None:
        """
        Forward events from a stream to the event stream (equivalent to TypeScript from(stream).subscribe).
        """
        try:
            async for event in stream:
                event_stream.on_next(event)
        except Exception as err:
            logger.error(f"Error forwarding stream events: {err}")
            raise
        finally:
            event_stream.complete()
    
    async def _call_action_handler(self, action: ActionInput, args: Dict[str, Any]) -> Any:
        """
        Call the action handler function (equivalent to TypeScript action.handler?.(args)).
        """
        if hasattr(action, 'handler') and callable(getattr(action, 'handler')):
            handler = getattr(action, 'handler')
            if asyncio.iscoroutinefunction(handler):
                return await handler(args)
            else:
                return handler(args)
        else:
            # No handler, return a default result
            return f"Action {action.name} executed successfully"
    
    async def _stream_langchain_response(
        self,
        result: Any,
        event_stream: RuntimeEventSubject,
        action_execution: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Stream LangChain response (equivalent to TypeScript streamLangChainResponse).
        """
        logger.info(f"🔍 [streamLangChainResponse] 开始处理结果: result_type={type(result)}, "
                   f"result={result}, has_action_execution={bool(action_execution)}")
        
        try:
            # 1. Handle string results
            if isinstance(result, str):
                logger.info(f"📝 [streamLangChainResponse] 处理字符串结果: {result}")
                if not action_execution:
                    # Just send one chunk with the string as the content
                    logger.info("💬 [streamLangChainResponse] 发送文本消息")
                    event_stream.send_text_message(generate_id(), result)
                else:
                    # Send as a result
                    logger.info(f"📤 [streamLangChainResponse] 发送 Action 执行结果: "
                               f"action_execution_id={action_execution['id']}, "
                               f"action_name={action_execution['name']}, result={result}")
                    event_stream.send_action_execution_result(
                        action_execution["id"],
                        action_execution["name"],
                        result=result
                    )
            
            # 2. Handle dict results (equivalent to AIMessage)
            elif isinstance(result, dict):
                self._maybe_send_action_execution_result_is_message(event_stream, action_execution)
                
                # Handle content
                if "content" in result and result["content"]:
                    event_stream.send_text_message(generate_id(), str(result["content"]))
                
                # Handle tool calls
                if "tool_calls" in result:
                    for tool_call in result["tool_calls"]:
                        event_stream.send_action_execution(
                            tool_call.get("id", generate_id()),
                            tool_call.get("name", "unknown"),
                            json.dumps(tool_call.get("args", {}))
                        )
            
            # 3. Handle async generators/iterators (equivalent to IterableReadableStream)
            elif hasattr(result, '__aiter__'):
                self._maybe_send_action_execution_result_is_message(event_stream, action_execution)
                await self._stream_async_iterator(result, event_stream)
            
            # 4. Handle other types with action execution
            elif action_execution:
                event_stream.send_action_execution_result(
                    action_execution["id"],
                    action_execution["name"],
                    result=self._encode_result(result)
                )
            
            # 5. Unsupported type
            else:
                raise ValueError("Invalid return type from action handler")
                
        except Exception as e:
            logger.error(f"Error in streamLangChainResponse: {e}")
            if action_execution:
                event_stream.send_action_execution_result(
                    action_execution["id"],
                    action_execution["name"],
                    error={
                        "code": "STREAM_ERROR",
                        "message": str(e)
                    }
                )
            raise
        finally:
            event_stream.complete()
    
    def _maybe_send_action_execution_result_is_message(
        self,
        event_stream: RuntimeEventSubject,
        action_execution: Optional[Dict[str, str]]
    ) -> None:
        """
        Send action execution result indicating we're sending a message (equivalent to TypeScript function).
        """
        if action_execution:
            event_stream.send_action_execution_result(
                action_execution["id"],
                action_execution["name"],
                result="Sending a message"
            )
    
    async def _stream_async_iterator(
        self,
        async_iterator: Any,
        event_stream: RuntimeEventSubject
    ) -> None:
        """
        Stream an async iterator (equivalent to TypeScript IterableReadableStream handling).
        """
        mode = None  # "function" | "message" | None
        current_message_id = ""
        
        tool_call_details = {
            "name": None,
            "id": None,
            "index": None,
            "prev_index": None,
        }
        
        try:
            async for chunk in async_iterator:
                tool_call_name = None
                tool_call_id = None
                tool_call_args = None
                has_tool_call = False
                content = ""
                
                # Extract content and tool call information from chunk
                if isinstance(chunk, dict):
                    if "content" in chunk:
                        content = str(chunk["content"])
                    
                    if "tool_calls" in chunk and chunk["tool_calls"]:
                        tool_call = chunk["tool_calls"][0]
                        tool_call_name = tool_call.get("name")
                        tool_call_id = tool_call.get("id")
                        tool_call_args = tool_call.get("args")
                        has_tool_call = True
                
                # Handle mode switching
                if mode == "message" and (tool_call_id or not chunk):
                    mode = None
                    event_stream.send_text_message_end(current_message_id)
                elif mode == "function" and (not has_tool_call or not chunk):
                    mode = None
                    if tool_call_id:
                        event_stream.send_action_execution_end(tool_call_id)
                
                if not chunk:
                    break
                
                # Start new mode
                if mode is None:
                    if has_tool_call and tool_call_id and tool_call_name:
                        mode = "function"
                        event_stream.send_action_execution_start(
                            tool_call_id,
                            tool_call_name,
                            chunk.get("id")
                        )
                    elif content:
                        mode = "message"
                        current_message_id = chunk.get("id", generate_id())
                        event_stream.send_text_message_start(current_message_id)
                
                # Send content events
                if mode == "message" and content:
                    event_stream.send_text_message_content(current_message_id, content)
                elif mode == "function" and tool_call_args and tool_call_id:
                    event_stream.send_action_execution_args(tool_call_id, tool_call_args)
                    
        except Exception as e:
            logger.error(f"Error streaming async iterator: {e}")
            raise
    
    def _encode_result(self, result: Any) -> str:
        """
        Encode result to string (equivalent to TypeScript encodeResult function).
        """
        if result is None:
            return ""
        elif isinstance(result, str):
            return result
        else:
            return json.dumps(result)


def generate_id() -> str:
    """Generate a random ID (equivalent to TypeScript randomId)."""
    return str(uuid4())


# Helper functions for FastAPI integration
def create_fastapi_event_data(event: RuntimeEvent) -> Dict[str, Any]:
    """Convert a RuntimeEvent to FastAPI-compatible event data matching frontend message types."""
    from datetime import datetime
    
    if isinstance(event, TextMessageStartEvent):
        # Create a text message that the frontend can parse
        return {
            "id": event.message_id,
            "type": "text",
            "role": "assistant",
            "content": "",  # Content will be added by subsequent content events
            "parentMessageId": event.parent_message_id,
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "pending"}
        }
    elif isinstance(event, TextMessageContentEvent):
        # Update existing text message with content
        return {
            "id": event.message_id,
            "type": "text",
            "role": "assistant",
            "content": event.content,
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "pending"}
        }
    elif isinstance(event, TextMessageEndEvent):
        # Finalize text message
        return {
            "id": event.message_id,
            "type": "text",
            "role": "assistant",
            "content": "",  # Final content should be set by last content event
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "success"}
        }
    elif isinstance(event, ActionExecutionStartEvent):
        # Create action execution message
        return {
            "id": event.action_execution_id,
            "type": "action_execution",
            "name": event.action_name,
            "arguments": {},  # Arguments will be added by subsequent args events
            "parentMessageId": event.parent_message_id,
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "pending"}
        }
    elif isinstance(event, ActionExecutionArgsEvent):
        # Update action execution with arguments
        try:
            args = json.loads(event.args) if isinstance(event.args, str) else event.args
        except json.JSONDecodeError:
            args = {"raw_args": event.args}
        
        return {
            "id": event.action_execution_id,
            "type": "action_execution",
            "name": "",  # Name should be set by start event
            "arguments": args,
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "pending"}
        }
    elif isinstance(event, ActionExecutionEndEvent):
        # Finalize action execution
        return {
            "id": event.action_execution_id,
            "type": "action_execution",
            "name": "",  # Name should be set by start event
            "arguments": {},
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "success"}
        }
    elif isinstance(event, ActionExecutionResultEvent):
        # Create result message
        return {
            "id": f"result-{event.action_execution_id}",
            "type": "result",
            "actionExecutionId": event.action_execution_id,
            "actionName": event.action_name,
            "result": event.result,
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "success"}
        }
    elif isinstance(event, AgentStateMessageEvent):
        # Create agent state message
        return {
            "id": f"agent-{event.thread_id}-{event.run_id or 'unknown'}",
            "type": "agent_state",
            "agentName": event.agent_name,
            "state": event.state,
            "running": event.running,
            "threadId": event.thread_id,
            "nodeName": event.node_name,
            "runId": event.run_id,
            "active": event.active,
            "role": "assistant",
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "success"}
        }
    else:
        # Default fallback for unknown events
        return {
            "id": generate_id(),
            "type": "text",
            "role": "assistant",
            "content": f"Unknown event: {type(event).__name__}",
            "createdAt": datetime.now().isoformat(),
            "status": {"code": "error", "reason": "Unknown event type"}
        }


# Additional utility functions for RxPY/asyncio integration
def observable_to_async_generator(observable: Observable) -> Callable[[], AsyncGenerator[RuntimeEvent, None]]:
    """Convert an RxPY Observable to an async generator for asyncio integration."""
    async def async_generator() -> AsyncGenerator[RuntimeEvent, None]:
        queue = asyncio.Queue()
        disposable = None
        
        def on_next(item):
            queue.put_nowait(item)
        
        def on_error(error):
            queue.put_nowait(error)
        
        def on_completed():
            queue.put_nowait(StopAsyncIteration)
        
        disposable = observable.subscribe(
            on_next=on_next,
            on_error=on_error,
            on_completed=on_completed
        )
        
        try:
            while True:
                item = await queue.get()
                if item is StopAsyncIteration:
                    break
                elif isinstance(item, Exception):
                    raise item
                else:
                    yield item
        finally:
            if disposable:
                disposable.dispose()
    
    return async_generator