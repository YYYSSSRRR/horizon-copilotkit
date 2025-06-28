"""
Event system for CopilotKit Python Runtime

This module provides the event system for handling runtime events,
maintaining compatibility with the TypeScript version.
"""

import asyncio
from typing import Dict, Any, Callable, List, Optional
from enum import Enum
from datetime import datetime


class RuntimeEventTypes(Enum):
    """Runtime event types"""
    MESSAGE = "message"
    MESSAGE_CHUNK = "message_chunk"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPLETION = "completion"
    ERROR = "error"
    AGENT_STATE = "agent_state"
    EXTENSION = "extension"


class RuntimeEvent:
    """Runtime event"""
    
    def __init__(self, event_type: RuntimeEventTypes, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()


class RuntimeEventSource:
    """Event source for runtime events"""
    
    def __init__(self):
        self._listeners: Dict[RuntimeEventTypes, List[Callable[[Dict[str, Any]], None]]] = {}
        self._async_listeners: Dict[RuntimeEventTypes, List[Callable[[Dict[str, Any]], None]]] = {}
        self._events: List[RuntimeEvent] = []
        self._closed = False
    
    def on(self, event_type: RuntimeEventTypes, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Add event listener"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
    
    def on_async(self, event_type: RuntimeEventTypes, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Add async event listener"""
        if event_type not in self._async_listeners:
            self._async_listeners[event_type] = []
        self._async_listeners[event_type].append(listener)
    
    def off(self, event_type: RuntimeEventTypes, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove event listener"""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass
    
    def emit(self, event_type: RuntimeEventTypes, data: Dict[str, Any]) -> None:
        """Emit event"""
        if self._closed:
            return
        
        event = RuntimeEvent(event_type, data)
        self._events.append(event)
        
        # Call sync listeners
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                try:
                    listener(data)
                except Exception as e:
                    print(f"Error in event listener: {e}")
        
        # Call async listeners
        if event_type in self._async_listeners:
            for listener in self._async_listeners[event_type]:
                try:
                    asyncio.create_task(listener(data))
                except Exception as e:
                    print(f"Error in async event listener: {e}")
    
    async def emit_async(self, event_type: RuntimeEventTypes, data: Dict[str, Any]) -> None:
        """Emit event asynchronously"""
        if self._closed:
            return
        
        event = RuntimeEvent(event_type, data)
        self._events.append(event)
        
        # Call sync listeners
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                try:
                    listener(data)
                except Exception as e:
                    print(f"Error in event listener: {e}")
        
        # Call async listeners
        if event_type in self._async_listeners:
            tasks = []
            for listener in self._async_listeners[event_type]:
                try:
                    tasks.append(listener(data))
                except Exception as e:
                    print(f"Error in async event listener: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_events(self, event_type: Optional[RuntimeEventTypes] = None) -> List[RuntimeEvent]:
        """Get all events or events of specific type"""
        if event_type is None:
            return self._events.copy()
        return [event for event in self._events if event.type == event_type]
    
    def clear_events(self) -> None:
        """Clear all events"""
        self._events.clear()
    
    def close(self) -> None:
        """Close event source"""
        self._closed = True
        self._listeners.clear()
        self._async_listeners.clear()
    
    def is_closed(self) -> bool:
        """Check if event source is closed"""
        return self._closed 