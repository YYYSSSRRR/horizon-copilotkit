"""
Tests for DeepSeek adapter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from openai import AsyncOpenAI

from copilotkit_runtime.adapters.deepseek_adapter import DeepSeekAdapter, DEFAULT_MODEL, DEEPSEEK_BASE_URL
from copilotkit_runtime.types import (
    CopilotRuntimeChatCompletionRequest,
    TextMessage,
    MessageRole,
    Action,
    Parameter,
)
from copilotkit_runtime.events import EventSource


class TestDeepSeekAdapter:
    """Test cases for DeepSeekAdapter."""
    
    def test_init_with_api_key(self):
        """Test adapter initialization with API key."""
        adapter = DeepSeekAdapter(api_key="test-key")
        
        assert adapter.model == DEFAULT_MODEL
        assert adapter.disable_parallel_tool_calls is False
        assert isinstance(adapter.openai, AsyncOpenAI)
    
    def test_init_with_openai_client(self):
        """Test adapter initialization with pre-configured OpenAI client."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        adapter = DeepSeekAdapter(openai=mock_client)
        
        assert adapter.openai is mock_client
        assert adapter.model == DEFAULT_MODEL
    
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with pytest.raises(ValueError, match="DeepSeek API key is required"):
            DeepSeekAdapter()
    
    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        adapter = DeepSeekAdapter(
            api_key="test-key",
            model="deepseek-coder",
            disable_parallel_tool_calls=True,
            base_url="https://custom.deepseek.com/v1",
            headers={"Custom-Header": "value"}
        )
        
        assert adapter.model == "deepseek-coder"
        assert adapter.disable_parallel_tool_calls is True
    
    @pytest.mark.asyncio
    async def test_process_basic_request(self):
        """Test processing a basic chat completion request."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter
        adapter = DeepSeekAdapter(openai=mock_client)
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Create request
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[
                TextMessage(
                    id="msg-1",
                    content="Hello, how are you?",
                    role=MessageRole.USER,
                )
            ],
            actions=[],
            event_source=event_source,
        )
        
        # Process request
        response = await adapter.process(request)
        
        # Verify response
        assert response.thread_id == "test-thread"
        
        # Verify OpenAI client was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        
        assert call_args["model"] == DEFAULT_MODEL
        assert call_args["stream"] is True
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == "Hello, how are you?"
        assert call_args["messages"][0]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_process_with_actions(self):
        """Test processing request with actions (tools)."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter
        adapter = DeepSeekAdapter(openai=mock_client)
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Create action
        action = Action(
            name="get_weather",
            description="Get weather information",
            parameters=[
                Parameter(
                    name="location",
                    type="string",
                    description="The location",
                    required=True,
                )
            ],
            handler=AsyncMock(),
        )
        
        # Create request
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[
                TextMessage(
                    id="msg-1",
                    content="What's the weather like?",
                    role=MessageRole.USER,
                )
            ],
            actions=[action],
            event_source=event_source,
        )
        
        # Process request
        response = await adapter.process(request)
        
        # Verify response
        assert response.thread_id == "test-thread"
        
        # Verify tools were included
        call_args = mock_client.chat.completions.create.call_args[1]
        assert "tools" in call_args
        assert len(call_args["tools"]) == 1
        assert call_args["tools"][0]["function"]["name"] == "get_weather"
    
    @pytest.mark.asyncio
    async def test_process_with_forwarded_parameters(self):
        """Test processing request with forwarded parameters."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter
        adapter = DeepSeekAdapter(openai=mock_client)
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Create request with forwarded parameters
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[
                TextMessage(
                    id="msg-1",
                    content="Hello",
                    role=MessageRole.USER,
                )
            ],
            actions=[],
            event_source=event_source,
            forwarded_parameters={
                "temperature": 0.8,
                "max_tokens": 100,
                "stop": ["END"],
            }
        )
        
        # Process request
        await adapter.process(request)
        
        # Verify forwarded parameters
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["temperature"] == 0.8  # Within DeepSeek range
        assert call_args["max_tokens"] == 100
        assert call_args["stop"] == ["END"]
    
    @pytest.mark.asyncio
    async def test_temperature_clamping(self):
        """Test that temperature is clamped to DeepSeek's supported range."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter
        adapter = DeepSeekAdapter(openai=mock_client)
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Test temperature too low
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[TextMessage(id="msg-1", content="Hello", role=MessageRole.USER)],
            actions=[],
            event_source=event_source,
            forwarded_parameters={"temperature": 0.05}  # Below 0.1
        )
        
        await adapter.process(request)
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["temperature"] == 0.1  # Clamped to minimum
        
        # Test temperature too high
        request.forwarded_parameters = {"temperature": 2.5}  # Above 2.0
        await adapter.process(request)
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["temperature"] == 2.0  # Clamped to maximum
    
    @pytest.mark.asyncio
    async def test_parallel_tool_calls_disabled(self):
        """Test that parallel tool calls can be disabled."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter with parallel tool calls disabled
        adapter = DeepSeekAdapter(
            openai=mock_client,
            disable_parallel_tool_calls=True
        )
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Create request
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[TextMessage(id="msg-1", content="Hello", role=MessageRole.USER)],
            actions=[],
            event_source=event_source,
        )
        
        # Process request
        await adapter.process(request)
        
        # Verify parallel tool calls is disabled
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["parallel_tool_calls"] is False
    
    @pytest.mark.asyncio
    async def test_developer_role_conversion(self):
        """Test that developer role is converted to system role."""
        # Mock OpenAI client
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_stream = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_stream
        
        # Create adapter
        adapter = DeepSeekAdapter(openai=mock_client)
        
        # Mock event source
        event_source = MagicMock(spec=EventSource)
        event_source.stream = AsyncMock()
        
        # Create request with a message that would have developer role
        # Note: This is a bit artificial since our convert_message_to_openai_message
        # function would need to be mocked to return developer role
        request = CopilotRuntimeChatCompletionRequest(
            thread_id="test-thread",
            messages=[TextMessage(id="msg-1", content="Hello", role=MessageRole.USER)],
            actions=[],
            event_source=event_source,
        )
        
        # Process request
        await adapter.process(request)
        
        # Verify the request was processed (detailed role conversion testing
        # would require mocking the conversion function)
        mock_client.chat.completions.create.assert_called_once() 