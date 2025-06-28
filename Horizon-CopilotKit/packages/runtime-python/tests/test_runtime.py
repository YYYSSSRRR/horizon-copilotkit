"""
Tests for CopilotKit Python Runtime

This module contains basic tests for the CopilotRuntime class.
"""

import pytest
import asyncio
from datetime import datetime

from copilotkit_runtime import (
    CopilotRuntime,
    OpenAIAdapter,
    Action,
    Parameter,
    Middleware,
    MessageRole,
    TextMessageInput,
    MessageInput,
    ActionInput,
    CopilotRuntimeRequest,
    GraphQLContext,
)
from copilotkit_runtime.adapters.base import EmptyAdapter
from copilotkit_runtime.exceptions import CopilotKitMisuseError


class TestCopilotRuntime:
    """Test cases for CopilotRuntime"""
    
    def test_runtime_initialization(self):
        """Test basic runtime initialization"""
        runtime = CopilotRuntime()
        assert runtime.actions == []
        assert runtime.remote_endpoint_definitions == []
        assert runtime.agents == {}
    
    def test_runtime_with_actions(self):
        """Test runtime initialization with actions"""
        def test_action(param: str) -> str:
            return f"Result: {param}"
        
        actions = [
            Action(
                name="test_action",
                description="A test action",
                parameters=[
                    Parameter(
                        name="param",
                        type="string",
                        description="Test parameter",
                        required=True,
                    )
                ],
                handler=test_action,
            )
        ]
        
        runtime = CopilotRuntime(actions=actions)
        assert len(runtime.actions) == 1
        assert runtime.actions[0].name == "test_action"
    
    def test_runtime_with_middleware(self):
        """Test runtime initialization with middleware"""
        async def before_request(options):
            pass
        
        async def after_request(options):
            pass
        
        middleware = Middleware(
            on_before_request=before_request,
            on_after_request=after_request,
        )
        
        runtime = CopilotRuntime(middleware=middleware)
        assert runtime.on_before_request is not None
        assert runtime.on_after_request is not None
    
    def test_mcp_validation(self):
        """Test MCP configuration validation"""
        # Should raise error when MCP servers provided without client factory
        with pytest.raises(CopilotKitMisuseError):
            CopilotRuntime(
                mcp_servers=[{"endpoint": "test"}],
                create_mcp_client=None,
            )
    
    @pytest.mark.asyncio
    async def test_empty_adapter_validation(self):
        """Test EmptyAdapter validation"""
        runtime = CopilotRuntime()
        adapter = EmptyAdapter()
        
        # Create a mock request
        request = CopilotRuntimeRequest(
            service_adapter=adapter,
            messages=[],
            actions=[],
            output_messages_promise=asyncio.Future(),
            graphql_context=GraphQLContext(),
        )
        
        # Should raise error when EmptyAdapter is used without agent session
        with pytest.raises(CopilotKitMisuseError):
            await runtime.process_runtime_request(request)
    
    def test_message_conversion(self):
        """Test message input to message conversion"""
        runtime = CopilotRuntime()
        
        message_input = MessageInput(
            id="test-id",
            created_at=datetime.now(),
            text_message=TextMessageInput(
                content="Hello world",
                role=MessageRole.USER,
            ),
        )
        
        messages = runtime._convert_gql_input_to_messages([message_input])
        assert len(messages) == 1
        assert messages[0].id == "test-id"
        assert messages[0].text_message.content == "Hello world"
    
    def test_tool_calls_deduplication(self):
        """Test tool calls deduplication"""
        runtime = CopilotRuntime()
        
        actions = [
            ActionInput(name="action1", description="First action"),
            ActionInput(name="action2", description="Second action"),
            ActionInput(name="action1", description="Duplicate action"),  # Should be removed
        ]
        
        deduplicated = runtime._flatten_tool_calls_no_duplicates(actions)
        assert len(deduplicated) == 2
        assert deduplicated[0].name == "action1"
        assert deduplicated[1].name == "action2"
    
    def test_provider_detection(self):
        """Test provider detection from adapter"""
        runtime = CopilotRuntime()
        
        openai_adapter = OpenAIAdapter()
        provider = runtime._detect_provider(openai_adapter)
        assert provider == "openai"


if __name__ == "__main__":
    pytest.main([__file__]) 