import { useCopilotRuntimeClient as useCopilotRuntimeClientFromContext } from "../context/copilot-context";

/**
 * 获取 CopilotKit 运行时客户端的 Hook
 * 
 * @returns CopilotRuntimeClient 实例
 * @throws Error 如果不在 CopilotKit Provider 中使用或未找到运行时客户端
 */
export function useCopilotRuntimeClient() {
  return useCopilotRuntimeClientFromContext();
} 