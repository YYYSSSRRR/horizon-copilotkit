"""
CopilotKit Approval System
人工审批系统 - 用于需要人工确认的工具调用
"""

from .approval_manager import (
    ApprovalManager,
    PendingToolCall,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus
)

from .middleware import (
    ApprovalMiddleware,
    create_approval_wrapper
)

from .conversational_approval import (
    ConversationalApprovalManager,
    create_conversational_approval_wrapper,
    create_approval_decision_handler,
    get_conversational_approval_manager
)

__all__ = [
    "ApprovalManager",
    "PendingToolCall", 
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalStatus",
    "ApprovalMiddleware",
    "create_approval_wrapper",
    "ConversationalApprovalManager",
    "create_conversational_approval_wrapper",
    "create_approval_decision_handler",
    "get_conversational_approval_manager"
]