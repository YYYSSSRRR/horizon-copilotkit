import { useEffect, useRef } from "react";
import { randomId } from "@copilotkit/shared";
import { useCopilotActions, useFrontendApprovalManager } from "../context/copilot-context";
import { FrontendAction } from "../types/frontend-action";

/**
 * 注册一个 Copilot 动作的 Hook
 * 
 * @param action 要注册的动作定义
 * @param dependencies 依赖数组，当依赖变化时重新注册动作
 */
export function useCopilotAction<T extends any[] = any[]>(
  action: FrontendAction<T>,
  dependencies?: React.DependencyList
) {
  const { setAction, removeAction } = useCopilotActions();
  const approvalManager = useFrontendApprovalManager();
  const actionIdRef = useRef<string>();

  useEffect(() => {
    // 生成唯一的动作 ID
    if (!actionIdRef.current) {
      actionIdRef.current = `${action.name}-${randomId()}`;
    }

    const actionId = actionIdRef.current;

    // 如果动作需要审批且有审批管理器，则包装处理器
    let wrappedAction = action as FrontendAction;
    
    if (action.requireApproval && action.handler && approvalManager) {
      const originalHandler = action.handler;
      
      wrappedAction = {
        ...action,
        handler: async (args: any) => {
          try {
            // 请求审批
            const approvalRequest = approvalManager.requestApproval(action.name, args);
            
            // 生成审批消息
            const approvalMessage = approvalManager.generateApprovalMessage(approvalRequest);
            
            // 返回审批提示消息，而不是直接执行动作
            // 这会让AI看到审批请求，然后等待用户响应
            return approvalMessage;
          } catch (error) {
            console.error("审批请求失败:", error);
            throw error;
          }
        }
      } as any;
      
      // 将需要审批的动作添加到审批管理器
      approvalManager.addApprovalRequiredAction(action.name);
    }

    // 注册动作
    setAction(actionId, wrappedAction as any);

    // 清理函数：移除动作
    return () => {
      removeAction(actionId);
      if (action.requireApproval && approvalManager) {
        approvalManager.removeApprovalRequiredAction(action.name);
      }
    };
  }, dependencies ? [...dependencies, action.name] : [action.name, action.description, action.handler, action.requireApproval]);

  // 返回动作 ID，用于可能的手动控制
  return actionIdRef.current;
}

/**
 * 获取所有已注册的动作
 */
export function useRegisteredActions(): FrontendAction[] {
  const { actions }: { actions: FrontendAction[] } = useCopilotActions();
  return actions;
}

/**
 * 手动添加和移除动作的 Hook
 */
export function useCopilotActionManager() {
  const { setAction, removeAction } = useCopilotActions();

  const addAction = (action: FrontendAction, id?: string) => {
    const actionId = id || `${action.name}-${randomId()}`;
    setAction(actionId, action);
    return actionId;
  };

  return {
    addAction,
    removeAction,
  };
} 