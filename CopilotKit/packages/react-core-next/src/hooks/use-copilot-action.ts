import { useEffect, useRef } from "react";
import { randomId } from "@copilotkit/shared";
import { useCopilotActions, useFrontendInterruptManager, useCopilotContext } from "../context/copilot-context";
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
  const interruptManager = useFrontendInterruptManager();
  const { runtimeClient } = useCopilotContext();
  const actionIdRef = useRef<string>();

  useEffect(() => {
    // 生成唯一的动作 ID
    if (!actionIdRef.current) {
      actionIdRef.current = `${action.name}-${randomId()}`;
    }

    const actionId = actionIdRef.current;
    let wrappedAction = action as FrontendAction;
    
    // 异步中断机制：支持AI生成等异步操作
    if (action.asyncInterruptHandler && interruptManager) {
      console.log(`[中断系统] 注册动作 "${action.name}" 的异步中断处理器`);
      
      // 创建包装的中断处理器，支持异步操作
      const wrappedAsyncHandler = {
        onInterrupt: async (actionName: string, parameters: any, interruptId: string) => {
          return await action.asyncInterruptHandler!.onInterrupt(actionName, parameters, interruptId, runtimeClient);
        },
        onResume: action.asyncInterruptHandler.onResume
      };
      
      // 注册异步中断处理器到管理器
      interruptManager.registerInterruptAction(action.name, wrappedAsyncHandler);
      
      // 包装原始 handler，使用异步中断处理
      wrappedAction = {
        ...action,
        handler: async (args: any) => {
          try {
            console.log(`[中断系统] 异步动作 "${action.name}" 被调用，创建异步中断...`);
            
            // 先返回加载消息
            const loadingMessage = `🤖 **AI正在为您生成选项...**
            
动作: ${action.name}
参数: ${JSON.stringify(args, null, 2)}

请稍等，AI正在分析您的需求并生成个性化选项...`;

            // 在后台启动异步处理
            setTimeout(async () => {
              try {
                console.log(`[中断系统] 开始异步处理 "${action.name}"`);
                const { request, displayData } = await interruptManager.createInterruptAsync(action.name, args);
                console.log(`[中断系统] 异步中断已创建，ID: ${request.interruptId}`);
                console.log(`[中断系统] AI生成的数据:`, displayData);
                
                // displayData 应该包含AI生成的选项和UI显示逻辑
                // 这里由asyncInterruptHandler负责显示弹框等UI操作
              } catch (error) {
                console.error(`[中断系统] 异步中断处理失败:`, error);
              }
            }, 0);
            
            // 立即返回加载消息
            return loadingMessage;
          } catch (error) {
            console.error(`[中断系统] 异步中断创建失败:`, error);
            throw error;
          }
        }
      } as any;
    }
    // 新的中断机制：支持自定义中断处理器
    else if (action.interruptHandler && interruptManager) {
      console.log(`[中断系统] 注册动作 "${action.name}" 的中断处理器`);
      
      // 注册中断处理器到管理器
      interruptManager.registerInterruptAction(action.name, action.interruptHandler);
      
      // 包装原始 handler，在调用前进行中断
      wrappedAction = {
        ...action,
        handler: async (args: any) => {
          try {
            console.log(`[中断系统] 动作 "${action.name}" 被调用，创建中断...`);
            
            // 创建中断并获取显示数据
            const { request, displayData } = interruptManager.createInterrupt(action.name, args);
            
            console.log(`[中断系统] 中断已创建，ID: ${request.interruptId}`);
            
            // 返回显示数据给 AI，让用户看到中断信息
            return displayData;
          } catch (error) {
            console.error(`[中断系统] 中断创建失败:`, error);
            throw error;
          }
        }
      } as any;
    }
    // 向后兼容：支持旧的 requireApproval 机制
    else if (action.requireApproval && action.handler && interruptManager) {
      console.log(`[中断系统] 使用兼容模式为动作 "${action.name}" 设置审批中断`);
      
      // 创建默认的审批处理器
      const defaultApprovalHandler = {
        onInterrupt: (actionName: string, parameters: any, interruptId: string) => {
          return `🔐 **动作审批请求**

动作名称: ${actionName}
参数: ${JSON.stringify(parameters, null, 2)}
审批ID: ${interruptId.slice(-8)}
时间: ${new Date().toLocaleString()}

请回复 'y' 或 '同意' 批准此操作，或 'n' 或 '拒绝' 取消操作。

⚠️ **重要**: 当你批准或拒绝时，请使用审批ID "${interruptId.slice(-8)}" 来确保正确处理。`;
        },
        
        onResume: async (actionName: string, originalParameters: any, resumeData: any) => {
          const normalizedDecision = String(resumeData).toLowerCase().trim();
          const isApproved = ['y', 'yes', '同意', '是', 'approve', 'approved'].includes(normalizedDecision);
          
          if (!isApproved) {
            return `❌ 拒绝 - 动作 "${actionName}" 已被拒绝，操作已取消。`;
          }
          
          // 执行原始处理器
          if (action.handler) {
            const result = await action.handler(originalParameters);
            return `✅ 批准 - ${result}`;
          }
          
          return `✅ 批准 - 动作 "${actionName}" 已获批准并执行。`;
        }
      };
      
      // 注册默认审批处理器
      interruptManager.registerInterruptAction(action.name, defaultApprovalHandler);
      
      wrappedAction = {
        ...action,
        handler: async (args: any) => {
          try {
            const { request, displayData } = interruptManager.createInterrupt(action.name, args);
            return displayData;
          } catch (error) {
            console.error(`[中断系统] 审批中断创建失败:`, error);
            throw error;
          }
        }
      } as any;
    }

    // 注册动作
    setAction(actionId, wrappedAction as any);
    console.log(`[中断系统] 动作 "${action.name}" 已注册，ID: ${actionId}`);

    // 清理函数：移除动作和中断处理器
    return () => {
      console.log(`[中断系统] 清理动作 "${action.name}"`);
      removeAction(actionId);
      if ((action.asyncInterruptHandler || action.interruptHandler || action.requireApproval) && interruptManager) {
        interruptManager.unregisterInterruptAction(action.name);
        console.log(`[中断系统] 动作 "${action.name}" 的中断处理器已移除`);
      }
    };
  }, dependencies ? [...dependencies, action.name] : [
    action.name, 
    action.description, 
    action.handler, 
    action.requireApproval,
    action.interruptHandler,
    action.asyncInterruptHandler
  ]);

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