"""
审批管理器 - 管理待审批的工具调用
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union
from pydantic import BaseModel
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ApprovalStatus(str, Enum):
    """审批状态枚举"""
    PENDING = "pending"
    APPROVED_AND_EXECUTED = "approved_and_executed"
    APPROVED_BUT_FAILED = "approved_but_failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PendingToolCall(BaseModel):
    """待审批的工具调用"""
    approval_id: str
    session_id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str
    original_handler: Any  # 原始的处理函数
    
    class Config:
        arbitrary_types_allowed = True


class ApprovalRequest(BaseModel):
    """审批请求"""
    approval_id: str
    approved: bool


class ApprovalResponse(BaseModel):
    """审批响应"""
    approval_id: str
    status: ApprovalStatus
    result: Optional[str] = None
    error: Optional[str] = None


class ApprovalSystemStatus(BaseModel):
    """审批系统状态"""
    status: str
    pending_count: int
    total_capacity: int
    uptime: str
    features: Dict[str, Any]


class ApprovalManager:
    """审批管理器 - 单例模式"""
    
    _instance: Optional['ApprovalManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        self.pending_approvals: Dict[str, PendingToolCall] = {}
        self.max_capacity = 100
        self.start_time = datetime.now()
        self.logger = logger.bind(component="ApprovalManager")
        self._initialized = True
        
        self.logger.info("审批管理器已初始化")
    
    def create_approval_request(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        original_handler: Callable,
        session_id: str = "default_session"
    ) -> str:
        """创建审批请求"""
        if len(self.pending_approvals) >= self.max_capacity:
            raise ValueError(f"审批队列已满，最大容量: {self.max_capacity}")
        
        approval_id = str(uuid.uuid4())
        
        pending_call = PendingToolCall(
            approval_id=approval_id,
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            timestamp=datetime.now().isoformat(),
            original_handler=original_handler
        )
        
        self.pending_approvals[approval_id] = pending_call
        
        self.logger.info(
            "创建审批请求",
            approval_id=approval_id,
            tool_name=tool_name,
            session_id=session_id,
            arguments=arguments
        )
        
        return approval_id
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """获取所有待审批请求"""
        return [
            {
                "approval_id": req.approval_id,
                "session_id": req.session_id,
                "tool_name": req.tool_name,
                "arguments": req.arguments,
                "timestamp": req.timestamp,
            }
            for req in self.pending_approvals.values()
        ]
    
    async def process_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """处理审批请求"""
        approval_id = request.approval_id
        
        if approval_id not in self.pending_approvals:
            self.logger.warning("审批请求不存在", approval_id=approval_id)
            raise ValueError(f"审批请求不存在: {approval_id}")
        
        pending_call = self.pending_approvals.pop(approval_id)
        
        self.logger.info(
            "处理审批请求",
            approval_id=approval_id,
            approved=request.approved,
            tool_name=pending_call.tool_name
        )
        
        if request.approved:
            try:
                # 执行原始的工具调用
                result = await pending_call.original_handler(pending_call.arguments)
                
                self.logger.info(
                    "工具调用执行成功",
                    approval_id=approval_id,
                    tool_name=pending_call.tool_name,
                    result=str(result)[:200]  # 限制日志长度
                )
                
                return ApprovalResponse(
                    approval_id=approval_id,
                    status=ApprovalStatus.APPROVED_AND_EXECUTED,
                    result=str(result)
                )
                
            except Exception as e:
                self.logger.error(
                    "工具调用执行失败",
                    approval_id=approval_id,
                    tool_name=pending_call.tool_name,
                    error=str(e),
                    exc_info=True
                )
                
                return ApprovalResponse(
                    approval_id=approval_id,
                    status=ApprovalStatus.APPROVED_BUT_FAILED,
                    error=str(e)
                )
        else:
            self.logger.info(
                "工具调用被拒绝",
                approval_id=approval_id,
                tool_name=pending_call.tool_name
            )
            
            return ApprovalResponse(
                approval_id=approval_id,
                status=ApprovalStatus.REJECTED,
                result="工具调用被拒绝"
            )
    
    def cancel_approval(self, approval_id: str) -> Dict[str, str]:
        """取消审批请求"""
        if approval_id not in self.pending_approvals:
            raise ValueError(f"审批请求不存在: {approval_id}")
        
        cancelled_call = self.pending_approvals.pop(approval_id)
        
        self.logger.info(
            "取消审批请求",
            approval_id=approval_id,
            tool_name=cancelled_call.tool_name
        )
        
        return {"status": "cancelled", "approval_id": approval_id}
    
    def get_system_status(self) -> ApprovalSystemStatus:
        """获取审批系统状态"""
        uptime = datetime.now() - self.start_time
        uptime_str = f"{uptime.days}天 {uptime.seconds//3600}小时 {(uptime.seconds%3600)//60}分钟"
        
        return ApprovalSystemStatus(
            status="running",
            pending_count=len(self.pending_approvals),
            total_capacity=self.max_capacity,
            uptime=uptime_str,
            features={
                "auto_approval": False,
                "batch_approval": True,
                "approval_timeout": None,
                "max_capacity": self.max_capacity
            }
        )
    
    def clear_all_pending(self) -> int:
        """清空所有待审批请求（谨慎使用）"""
        count = len(self.pending_approvals)
        self.pending_approvals.clear()
        
        self.logger.warning("清空所有待审批请求", count=count)
        return count
    
    @classmethod
    def get_instance(cls) -> 'ApprovalManager':
        """获取审批管理器实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance