import { useEffect, useRef } from "react";
import { randomId } from "@copilotkit/shared";
import { useCopilotActions } from "../context/copilot-context";
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
  const actionIdRef = useRef<string>();

  useEffect(() => {
    // 生成唯一的动作 ID
    if (!actionIdRef.current) {
      actionIdRef.current = `${action.name}-${randomId()}`;
    }

    const actionId = actionIdRef.current;

    // 注册动作（类型转换以兼容 context）
    setAction(actionId, action as FrontendAction);

    // 清理函数：移除动作
    return () => {
      removeAction(actionId);
    };
  }, dependencies ? [...dependencies, action.name] : [action.name, action.description, action.handler]);

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