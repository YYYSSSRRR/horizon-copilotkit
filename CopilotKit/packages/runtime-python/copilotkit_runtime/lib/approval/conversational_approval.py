"""
对话式审批处理器 - 支持通过聊天对话进行审批
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel
import structlog

from .approval_manager import ApprovalManager, PendingToolCall, ApprovalStatus
from ..exceptions import ApprovalRequiredError

logger = structlog.get_logger(__name__)


class ConversationalApprovalManager(ApprovalManager):
    """
    对话式审批管理器 - 扩展基础审批管理器，支持通过对话进行审批
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logger.bind(component="ConversationalApprovalManager")
        self.logger.info("对话式审批管理器已初始化")
    
    def create_approval_request(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        original_handler: Callable,
        session_id: str = "default_session"
    ) -> str:
        """创建审批请求，返回对话式提示"""
        approval_id = super().create_approval_request(
            tool_name, arguments, original_handler, session_id
        )
        
        # 返回对话式审批提示消息
        return approval_id
    
    def get_approval_prompt(self, approval_id: str) -> str:
        """获取对话式审批提示消息"""
        if approval_id not in self.pending_approvals:
            return "❌ 审批请求不存在"
        
        pending_call = self.pending_approvals[approval_id]
        
        return (
            f"🔐 工具调用需要您的审批:\n"
            f"📊 工具名称: {pending_call.tool_name}\n"
            f"📋 调用参数: {pending_call.arguments}\n"
            f"🆔 审批ID: {approval_id[:8]}...\n\n"
            f"请回复:\n"
            f"• 'y' 或 'yes' 同意执行\n"
            f"• 'n' 或 'no' 拒绝执行\n\n"
            f"等待您的审批决定..."
        )
    
    async def handle_conversational_approval(
        self, 
        decision: str, 
        approval_id_partial: Optional[str] = None
    ) -> str:
        """
        处理对话式审批决定
        
        Args:
            decision: 用户的决定 (y/n/yes/no等)
            approval_id_partial: 可选的部分审批ID
            
        Returns:
            审批处理结果消息
        """
        decision = decision.lower().strip()
        
        if not decision:
            return "❌ 请指定您的决定: 'y'(同意) 或 'n'(拒绝)"
        
        # 检查是否有待审批的请求
        if not self.pending_approvals:
            return "✅ 当前没有待审批的工具调用请求。"
        
        # 查找目标审批请求
        target_approval = None
        approval_id = None
        
        if approval_id_partial:
            # 根据部分ID查找
            for aid, pending in self.pending_approvals.items():
                if aid.startswith(approval_id_partial):
                    target_approval = pending
                    approval_id = aid
                    break
        else:
            # 获取最近的一个请求（按时间戳排序）
            sorted_approvals = sorted(
                self.pending_approvals.items(), 
                key=lambda x: x[1].timestamp, 
                reverse=True
            )
            if sorted_approvals:
                approval_id, target_approval = sorted_approvals[0]
        
        if not target_approval:
            if approval_id_partial:
                return f"❌ 未找到ID以'{approval_id_partial}'开头的审批请求。"
            else:
                return "❌ 未找到待审批的请求。"
        
        # 从待审批列表中移除
        pending_call = self.pending_approvals.pop(approval_id)
        
        if decision in ['y', 'yes', '同意', '是']:
            # 用户同意，执行工具调用
            try:
                result = await pending_call.original_handler(pending_call.arguments)
                
                self.logger.info(
                    "用户批准并执行工具调用",
                    approval_id=approval_id,
                    tool_name=pending_call.tool_name,
                    result=str(result)[:200]
                )
                
                return (
                    f"✅ 已批准并执行工具调用!\n\n"
                    f"🔧 工具: {pending_call.tool_name}\n"
                    f"📋 参数: {pending_call.arguments}\n"
                    f"📊 执行结果:\n{result}"
                )
                       
            except Exception as e:
                self.logger.error(
                    "工具执行失败",
                    approval_id=approval_id,
                    tool_name=pending_call.tool_name,
                    error=str(e),
                    exc_info=True
                )
                
                return (
                    f"❌ 工具调用已批准但执行失败:\n"
                    f"🔧 工具: {pending_call.tool_name}\n"
                    f"📋 参数: {pending_call.arguments}\n"
                    f"💥 错误: {str(e)}"
                )
                       
        elif decision in ['n', 'no', '拒绝', '否']:
            # 用户拒绝
            self.logger.info(
                "用户拒绝工具调用",
                approval_id=approval_id,
                tool_name=pending_call.tool_name
            )
            
            return (
                f"❌ 工具调用已被拒绝\n\n"
                f"🔧 工具: {pending_call.tool_name}\n"
                f"📋 参数: {pending_call.arguments}\n"
                f"🚫 状态: 已拒绝执行"
            )
                   
        else:
            # 用户输入了无效的决定，将请求放回待审批列表
            self.pending_approvals[approval_id] = pending_call
            return (
                f"❓ 无效的决定 '{decision}'\n\n"
                f"请回复:\n"
                f"• 'y' 或 'yes' 同意执行\n"
                f"• 'n' 或 'no' 拒绝执行"
            )


def create_conversational_approval_wrapper(
    tool_name: str, 
    original_handler: Callable,
    approval_manager: Optional[ConversationalApprovalManager] = None
) -> Callable:
    """
    创建对话式审批包装器
    
    Args:
        tool_name: 工具名称
        original_handler: 原始处理函数
        approval_manager: 对话式审批管理器实例
    
    Returns:we
        包装后的处理函数
    """
    if approval_manager is None:
        approval_manager = ConversationalApprovalManager()
    
    async def approval_handler(arguments: Dict[str, Any]) -> str:
        # 检查是否是从审批执行中调用的（避免递归）
        if arguments.get('__approval_bypass', False):
            # 如果是审批执行，直接调用原始函数，不再需要审批
            return await original_handler(arguments)
            
        try:
            # 创建一个绕过审批的包装器，用于审批后的实际执行
            async def bypass_wrapper(args):
                # 添加绕过标记
                bypass_args = dict(args)
                bypass_args['__approval_bypass'] = True
                return await approval_handler(bypass_args)
            
            # 创建审批请求，使用绕过包装器作为处理函数
            approval_id = approval_manager.create_approval_request(
                tool_name=tool_name,
                arguments=arguments,
                original_handler=bypass_wrapper,
                session_id=arguments.get('session_id', 'default_session')
            )
            
            logger.info(
                "工具调用需要审批",
                tool_name=tool_name,
                approval_id=approval_id,
                arguments=arguments
            )
            
            # 获取审批提示消息并直接返回（对话式审批）
            approval_message = approval_manager.get_approval_prompt(approval_id)
            return approval_message
        except Exception as e:
            logger.error(
                "创建审批请求失败",
                tool_name=tool_name,
                arguments=arguments,
                error=str(e),
                exc_info=True
            )
            return f"❌ 审批系统错误: {str(e)}。请联系管理员。"
    
    return approval_handler


def create_approval_decision_handler(
    approval_manager: Optional[ConversationalApprovalManager] = None
) -> Callable:
    """
    创建审批决定处理器
    
    Args:
        approval_manager: 对话式审批管理器实例
        
    Returns:
        审批决定处理函数
    """
    if approval_manager is None:
        approval_manager = ConversationalApprovalManager()
    
    async def handle_approval(arguments: Dict[str, Any]) -> str:
        """处理用户的审批决定"""
        decision = arguments.get("decision", "")
        approval_id_partial = arguments.get("approval_id", "")
        
        return await approval_manager.handle_conversational_approval(
            decision=decision,
            approval_id_partial=approval_id_partial
        )
    
    return handle_approval


# 全局实例，用于简化使用
_global_conversational_manager = None

def get_conversational_approval_manager() -> ConversationalApprovalManager:
    """获取全局对话式审批管理器实例"""
    global _global_conversational_manager
    if _global_conversational_manager is None:
        _global_conversational_manager = ConversationalApprovalManager()
    return _global_conversational_manager