import { useEffect, useRef, useState, useCallback } from "react";
import { randomId } from "@copilotkit/shared";
import { useCopilotContext, useCopilotCoAgentStateRenders } from "../context/copilot-context";
import { CoAgentStateRender } from "../types/coagent-action";
import { CoagentState } from "../types/coagent-state";
import { Message, TextMessage } from "../client/message-types";

export interface HintFunctionParams {
  /**
   * The previous state of the agent.
   */
  previousState: any;
  /**
   * The current state of the agent.
   */
  currentState: any;
}

export type HintFunction = (params: HintFunctionParams) => Message | undefined;

export interface UseCoAgentOptions {
  /**
   * CoAgent 的名称
   */
  name: string;

  /**
   * 初始状态
   */
  initialState?: any;

  /**
   * 状态渲染器
   */
  render?: CoAgentStateRender["render"];

  /**
   * 状态处理器
   */
  handler?: CoAgentStateRender["handler"];

  /**
   * 节点名称（可选）
   */
  nodeName?: string;

  /**
   * 状态变化回调
   */
  onStateChange?: (state: CoagentState) => void;

  /**
   * 错误处理回调
   */
  onError?: (error: Error) => void;
}

/**
 * CoAgent 状态管理 Hook
 */
export function useCoAgent(options: UseCoAgentOptions) {
  const { runtimeClient, threadId } = useCopilotContext();
  const { setCoAgentStateRender, removeCoAgentStateRender } = useCopilotCoAgentStateRenders();
  
  const [state, setState] = useState<CoagentState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const renderIdRef = useRef<string>();

  // 注册状态渲染器
  useEffect(() => {
    if (options.render || options.handler) {
      if (!renderIdRef.current) {
        renderIdRef.current = `coagent-${options.name}-${randomId()}`;
      }

      const renderId = renderIdRef.current;
      const render: CoAgentStateRender = {
        name: options.name,
        nodeName: options.nodeName,
        render: options.render,
        handler: options.handler,
      };

      setCoAgentStateRender(renderId, render);

      return () => {
        removeCoAgentStateRender(renderId);
      };
    }
  }, [options.name, options.nodeName, options.render, options.handler]);

  /**
   * 加载 CoAgent 状态
   */
  const loadState = useCallback(async () => {
    if (!runtimeClient || !threadId) {
      const error = new Error("Runtime client or thread ID not available");
      setError(error);
      options.onError?.(error);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await runtimeClient.loadAgentState({
        agentName: options.name,
        threadId,
      });

      const newState: CoagentState = {
        name: response.agentName,
        state: response.state,
        running: response.running,
        threadId: response.threadId,
        nodeName: response.nodeName,
        runId: response.runId,
        active: response.active,
        lastUpdated: new Date(),
      };

      setState(newState);
      options.onStateChange?.(newState);
    } catch (error) {
      const err = error as Error;
      setError(err);
      options.onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [runtimeClient, threadId, options.name, options.onStateChange, options.onError]);

  /**
   * 更新 CoAgent 状态
   */
  const updateState = useCallback(
    async (newState: any) => {
      if (!runtimeClient || !threadId) {
        const error = new Error("Runtime client or thread ID not available");
        setError(error);
        options.onError?.(error);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await runtimeClient.updateAgentState(
          options.name,
          threadId,
          newState
        );

        const updatedState: CoagentState = {
          name: response.agentName,
          state: response.state,
          running: response.running,
          threadId: response.threadId,
          nodeName: response.nodeName,
          runId: response.runId,
          active: response.active,
          lastUpdated: new Date(),
        };

        setState(updatedState);
        options.onStateChange?.(updatedState);
      } catch (error) {
        const err = error as Error;
        setError(err);
        options.onError?.(err);
      } finally {
        setIsLoading(false);
      }
    },
    [runtimeClient, threadId, options.name, options.onStateChange, options.onError]
  );

  /**
   * 启动 CoAgent
   */
  const start = useCallback(
    async (config?: any) => {
      if (!runtimeClient) {
        const error = new Error("Runtime client not available");
        setError(error);
        options.onError?.(error);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        await runtimeClient.startAgent(options.name, config);
        
        // 启动后加载状态
        if (threadId) {
          await loadState();
        }
      } catch (error) {
        const err = error as Error;
        setError(err);
        options.onError?.(err);
      } finally {
        setIsLoading(false);
      }
    },
    [runtimeClient, options.name, threadId, loadState, options.onError]
  );

  /**
   * 停止 CoAgent
   */
  const stop = useCallback(async () => {
    if (!runtimeClient) {
      const error = new Error("Runtime client not available");
      setError(error);
      options.onError?.(error);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await runtimeClient.stopAgent(options.name);
      
      // 停止后更新状态
      if (state) {
        setState({
          ...state,
          running: false,
          active: false,
          lastUpdated: new Date(),
        });
      }
    } catch (error) {
      const err = error as Error;
      setError(err);
      options.onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [runtimeClient, options.name, state, options.onError]);

  /**
   * 运行 CoAgent（重新运行）
   */
  const run = useCallback(
    async (hint?: HintFunction) => {
      if (!runtimeClient || !threadId) {
        const error = new Error("Runtime client or thread ID not available");
        setError(error);
        options.onError?.(error);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // 如果有提示，先发送提示消息
        if (hint && state) {
          const hintMessage = hint({
            previousState: state.state,
            currentState: state.state,
          });
          
          if (hintMessage) {
            // 通过聊天接口发送提示消息
            // 这里简化处理，实际可能需要更复杂的逻辑
            console.log("Hint message:", hintMessage);
          }
        }

        // 重新启动 agent
        await runtimeClient.startAgent(options.name);
        
        // 加载最新状态
        if (threadId) {
          await loadState();
        }
      } catch (error) {
        const err = error as Error;
        setError(err);
        options.onError?.(err);
      } finally {
        setIsLoading(false);
      }
    },
    [runtimeClient, threadId, options.name, state, loadState, options.onError]
  );

  // 初始化加载状态
  useEffect(() => {
    if (runtimeClient && threadId && !state) {
      loadState();
    }
  }, [runtimeClient, threadId, loadState]);

  // 设置初始状态
  useEffect(() => {
    if (options.initialState && !state) {
      setState({
        name: options.name,
        state: options.initialState,
        running: false,
        threadId: threadId || "",
        active: false,
        lastUpdated: new Date(),
      });
    }
  }, [options.initialState, options.name, threadId, state]);

  return {
    // 状态
    state: state?.state,
    coagentState: state,
    isLoading,
    error,
    running: state?.running || false,
    isActive: state?.active || false,

    // 操作
    loadState,
    updateState,
    setState: updateState,
    start,
    stop,
    run,

    // 元数据
    name: options.name,
    nodeName: state?.nodeName,
    runId: state?.runId,
    threadId: state?.threadId,
    lastUpdated: state?.lastUpdated,
  };
}

// 兼容性导出函数
export function startAgent(name: string, context: any) {
  if (context.runtimeClient) {
    return context.runtimeClient.startAgent(name);
  }
  throw new Error("Runtime client not available");
}

export function stopAgent(name: string, context: any) {
  if (context.runtimeClient) {
    return context.runtimeClient.stopAgent(name);
  }
  throw new Error("Runtime client not available");
}

export async function runAgent(
  name: string,
  context: any,
  appendMessage: (message: Message) => Promise<void>,
  runChatCompletion: () => Promise<Message[]>,
  hint?: HintFunction,
) {
  if (!context.runtimeClient) {
    throw new Error("Runtime client not available");
  }

  try {
    // 如果有提示，先发送提示消息
    if (hint && context.threadId) {
      const hintMessage = hint({
        previousState: {},
        currentState: {},
      });
      
      if (hintMessage) {
        await appendMessage(hintMessage);
      }
    }

    // 启动 agent
    await context.runtimeClient.startAgent(name);
    
    // 运行聊天完成
    return await runChatCompletion();
  } catch (error) {
    console.error("Error running agent:", error);
    throw error;
  }
} 