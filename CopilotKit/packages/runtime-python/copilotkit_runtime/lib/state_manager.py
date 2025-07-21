"""State management system using RxPy subjects."""

import asyncio
from typing import Any, Dict, List, Optional, Union
from rx.subject import ReplaySubject, Subject
from rx import operators as ops
from rx.core import Observer, Observable
import structlog

from ..api.models.responses import (
    SuccessResponseStatus, FailedResponseStatus,
    GuardrailsValidationFailureResponse, MessageStreamInterruptedResponse,
    UnknownErrorResponse, GuardrailsResult
)
from ..api.models.messages import (
    Message, SuccessMessageStatus, FailedMessageStatus
)

logger = structlog.get_logger(__name__)


class StateManager:
    """Manage various state subjects for event stream processing."""
    
    def __init__(self):
        """Initialize state manager with RxPy subjects."""
        # State tracking subjects
        self.response_status_subject = ReplaySubject()
        self.interrupt_streaming_subject = ReplaySubject()
        self.guardrails_result_subject = ReplaySubject()
        
        # Message collection
        self.output_messages: List[Message] = []
        self.output_messages_future: Optional[asyncio.Future] = None
        
        # Subscription tracking
        self.subscriptions: List[Any] = []
        
        self.logger = logger.bind(component="StateManager")
    
    def setup_output_messages_promise(self) -> asyncio.Future:
        """Setup promise for output messages collection."""
        self.output_messages_future = asyncio.Future()
        return self.output_messages_future
    
    def resolve_output_messages(self, messages: List[Message]):
        """Resolve output messages promise."""
        if self.output_messages_future and not self.output_messages_future.done():
            self.output_messages_future.set_result(messages)
    
    def reject_output_messages(self, error: Exception):
        """Reject output messages promise."""
        if self.output_messages_future and not self.output_messages_future.done():
            self.output_messages_future.set_exception(error)
    
    def add_output_message(self, message: Message):
        """Add message to output collection."""
        self.output_messages.append(message)
    
    def set_response_status(
        self, 
        status: Union[
            SuccessResponseStatus,
            FailedResponseStatus,
            GuardrailsValidationFailureResponse,
            MessageStreamInterruptedResponse,
            UnknownErrorResponse
        ]
    ):
        """Set response status."""
        self.response_status_subject.on_next(status)
    
    def interrupt_streaming(self, reason: str, message_id: Optional[str] = None):
        """Interrupt streaming with reason."""
        interrupt_data = {"reason": reason}
        if message_id:
            interrupt_data["message_id"] = message_id
        
        self.interrupt_streaming_subject.on_next(interrupt_data)
        self.logger.debug("Streaming interrupted", reason=reason, message_id=message_id)
    
    def set_guardrails_result(self, result: GuardrailsResult):
        """Set guardrails validation result."""
        self.guardrails_result_subject.on_next(result)
    
    def add_subscription(self, subscription: Any):
        """Add subscription for cleanup."""
        self.subscriptions.append(subscription)
    
    def cleanup(self):
        """Cleanup all subscriptions and resources."""
        self.logger.debug("Cleaning up state manager")
        
        for subscription in self.subscriptions:
            try:
                if hasattr(subscription, 'dispose'):
                    subscription.dispose()
                elif hasattr(subscription, 'unsubscribe'):
                    subscription.unsubscribe()
            except Exception as e:
                self.logger.warning("Error disposing subscription", error=str(e))
        
        self.subscriptions.clear()
        
        # Complete subjects
        try:
            self.response_status_subject.on_completed()
            self.interrupt_streaming_subject.on_completed()
            self.guardrails_result_subject.on_completed()
        except Exception as e:
            self.logger.warning("Error completing subjects", error=str(e))


class MessageStatusManager:
    """Manage message status tracking."""
    
    def __init__(self):
        """Initialize message status manager."""
        self.message_status_subjects: Dict[str, Subject] = {}
        self.logger = logger.bind(component="MessageStatusManager")
    
    def create_message_status_subject(self, message_id: str) -> Subject:
        """Create status subject for a message."""
        subject = Subject()
        self.message_status_subjects[message_id] = subject
        return subject
    
    def set_message_status(self, message_id: str, status: Union[SuccessMessageStatus, FailedMessageStatus]):
        """Set status for a specific message."""
        if message_id in self.message_status_subjects:
            self.message_status_subjects[message_id].on_next(status)
            self.logger.debug("Message status updated", message_id=message_id, status=status.code)
    
    def complete_message(self, message_id: str):
        """Complete status subject for a message."""
        if message_id in self.message_status_subjects:
            self.message_status_subjects[message_id].on_completed()
            del self.message_status_subjects[message_id]
    
    def fail_message(self, message_id: str, reason: str):
        """Fail a message with reason."""
        status = FailedMessageStatus(reason=reason)
        self.set_message_status(message_id, status)
        self.complete_message(message_id)
    
    def succeed_message(self, message_id: str):
        """Mark message as successful."""
        status = SuccessMessageStatus()
        self.set_message_status(message_id, status)
        self.complete_message(message_id)
    
    def cleanup(self):
        """Cleanup all message status subjects."""
        self.logger.debug("Cleaning up message status manager")
        
        for message_id, subject in self.message_status_subjects.items():
            try:
                subject.on_completed()
            except Exception as e:
                self.logger.warning("Error completing message status subject", 
                                  message_id=message_id, error=str(e))
        
        self.message_status_subjects.clear()