"""
审批中间件 - 创建需要审批的工具包装器
"""

import asyncio
from typing import Dict, Any, Callable, Set, List, Optional
from functools import wraps
import structlog

from .approval_manager import ApprovalManager

logger = structlog.get_logger(__name__)


def create_approval_wrapper(
    tool_name: str, 
    original_handler: Callable,
    approval_manager: Optional[ApprovalManager] = None
) -> Callable:
    """
    创建需要审批的工具包装器
    
    Args:
        tool_name: 工具名称
        original_handler: 原始处理函数
        approval_manager: 审批管理器实例（可选）
    
    Returns:
        包装后的处理函数
    """
    if approval_manager is None:
        approval_manager = ApprovalManager.get_instance()
    
    @wraps(original_handler)
    async def approval_handler(arguments: Dict[str, Any]) -> str:
        try:
            # 创建审批请求
            approval_id = approval_manager.create_approval_request(
                tool_name=tool_name,
                arguments=arguments,
                original_handler=original_handler,
                session_id=arguments.get('session_id', 'default_session')
            )
            
            logger.info(
                "工具调用需要审批",
                tool_name=tool_name,
                approval_id=approval_id,
                arguments=arguments
            )
            
            # 返回审批提示消息
            return (
                f"⏸️ 工具调用 '{tool_name}' 需要人工审批。\n\n"
                f"📋 **参数**: {arguments}\n\n"
                f"🆔 **审批ID**: `{approval_id}`\n\n"
                f"📋 请使用以下方式进行审批：\n"
                f"- 📱 Web管理界面: 访问审批面板\n"
                f"- 🔗 API调用: `POST /api/approvals/approve`\n"
                f"- 📋 查看待审批列表: `GET /api/approvals/pending`\n\n"
                f"⏱️ 请及时处理此审批请求。"
            )
            
        except Exception as e:
            logger.error(
                "创建审批请求失败",
                tool_name=tool_name,
                arguments=arguments,
                error=str(e),
                exc_info=True
            )
            # 如果审批系统出错，可以选择直接执行或返回错误
            # 这里选择返回错误信息
            return f"❌ 审批系统错误: {str(e)}。请联系管理员。"
    
    return approval_handler


class ApprovalMiddleware:
    """
    审批中间件 - 用于配置哪些工具需要审批
    """
    
    def __init__(
        self,
        approval_required_tools: Optional[Set[str]] = None,
        approval_manager: Optional[ApprovalManager] = None
    ):
        """
        初始化审批中间件
        
        Args:
            approval_required_tools: 需要审批的工具名称集合
            approval_manager: 审批管理器实例
        """
        self.approval_required_tools = approval_required_tools or set()
        self.approval_manager = approval_manager or ApprovalManager.get_instance()
        self.logger = logger.bind(component="ApprovalMiddleware")
        
        self.logger.info(
            "审批中间件已初始化",
            approval_required_tools=list(self.approval_required_tools)
        )
    
    def add_approval_required_tool(self, tool_name: str):
        """添加需要审批的工具"""
        self.approval_required_tools.add(tool_name)
        self.logger.info("添加审批工具", tool_name=tool_name)
    
    def remove_approval_required_tool(self, tool_name: str):
        """移除需要审批的工具"""
        self.approval_required_tools.discard(tool_name)
        self.logger.info("移除审批工具", tool_name=tool_name)
    
    def is_approval_required(self, tool_name: str) -> bool:
        """检查工具是否需要审批"""
        return tool_name in self.approval_required_tools
    
    def wrap_action_if_needed(self, action_name: str, original_handler: Callable) -> Callable:
        """如果需要，包装动作处理函数"""
        if self.is_approval_required(action_name):
            self.logger.info(
                "包装动作为审批模式",
                action_name=action_name
            )
            # 如果使用的是对话式审批管理器，使用对话式包装器
            from .conversational_approval import ConversationalApprovalManager, create_conversational_approval_wrapper
            if isinstance(self.approval_manager, ConversationalApprovalManager):
                return create_conversational_approval_wrapper(
                    tool_name=action_name,
                    original_handler=original_handler,
                    approval_manager=self.approval_manager
                )
            else:
                return create_approval_wrapper(
                    tool_name=action_name,
                    original_handler=original_handler,
                    approval_manager=self.approval_manager
                )
        else:
            return original_handler
    
    def wrap_actions(self, actions: List[Any]) -> List[Any]:
        """
        批量包装动作
        
        Args:
            actions: 动作列表
            
        Returns:
            处理后的动作列表
        """
        wrapped_actions = []
        
        for action in actions:
            # 检查动作是否有名称和处理函数
            if hasattr(action, 'name') and hasattr(action, 'handler'):
                original_handler = action.handler
                wrapped_handler = self.wrap_action_if_needed(action.name, original_handler)
                
                # 创建新的动作对象，更新处理函数
                if wrapped_handler != original_handler:
                    # 如果被包装了，更新动作
                    action.handler = wrapped_handler
                    # 可以选择更新描述，标明需要审批
                    if hasattr(action, 'description'):
                        if not action.description.endswith('（需要人工审批）'):
                            action.description = f"{action.description}（需要人工审批）"
            
            wrapped_actions.append(action)
        
        self.logger.info(
            "完成动作包装",
            total_actions=len(actions),
            approval_actions=sum(1 for a in actions if self.is_approval_required(getattr(a, 'name', '')))
        )
        
        return wrapped_actions
    
    def get_configuration(self) -> Dict[str, Any]:
        """获取中间件配置信息"""
        return {
            "approval_required_tools": list(self.approval_required_tools),
            "total_approval_tools": len(self.approval_required_tools),
            "approval_manager_status": self.approval_manager.get_system_status().dict()
        }