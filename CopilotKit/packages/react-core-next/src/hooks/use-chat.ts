import React, { useCallback, useRef, useMemo, useEffect } from "react";
import { randomId } from "@copilotkit/shared";
import { 
  Message, 
  TextMessage, 
  ActionExecutionMessage, 
  ResultMessage, 
  AgentStateMessage 
} from "../client/message-types";
import { FrontendAction } from "../types/frontend-action";
import { CoAgentStateRender } from "../types/coagent-action";
import { CoagentState } from "../types/coagent-state";
import { CopilotRuntimeClient } from "../client/copilot-runtime-client";

/**
 * 代理会话类型
 */
export interface AgentSession {
  agentName: string;
  threadId: string;
  status: "running" | "waiting" | "completed" | "failed";
  metadata?: Record<string, any>;
}

/**
 * 扩展输入类型
 */
export interface ExtensionsInput {
  [key: string]: any;
}

/**
 * Copilot API 配置类型
 */
export interface CopilotApiConfig {
  chatApiEndpoint: string;
  publicApiKey?: string;
  headers?: Record<string, string>;
  credentials?: RequestCredentials;
  cloud?: {
    guardrails?: {
      input?: {
        restrictToTopic?: {
          enabled: boolean;
          validTopics?: string[];
          invalidTopics?: string[];
        };
      };
    };
  };
  properties?: Record<string, any>;
  mcpServers?: any[];
}

/**
 * LangGraph 中断事件
 */
export interface LangGraphInterruptEvent {
  name: string;
  value?: any;
  response?: string;
}

/**
 * LangGraph 中断动作
 */
export interface LangGraphInterruptAction {
  id: string;
  event?: LangGraphInterruptEvent;
  render?: any;
  handler?: any;
  enabled?: any;
}

/**
 * 功能调用处理器类型
 */
export type FunctionCallHandler = (message: ActionExecutionMessage) => Promise<ResultMessage | void>;

/**
 * CoAgent 状态渲染处理器类型
 */
export type CoAgentStateRenderHandler = (render: CoAgentStateRender, state: any) => void;

/**
 * useChat Hook 的选项类型
 */
export type UseChatOptions = {
  /**
   * 聊天的初始消息，默认为空数组
   */
  initialMessages?: Message[];

  /**
   * 接收功能调用时的回调函数
   */
  onFunctionCall?: FunctionCallHandler;

  /**
   * 接收 CoAgent 动作时的回调函数
   */
  onCoAgentStateRender?: CoAgentStateRenderHandler;

  /**
   * 发送到 API 的前端动作列表
   */
  actions: FrontendAction<any>[];

  /**
   * CopilotKit API 配置
   */
  copilotConfig: CopilotApiConfig;

  /**
   * 当前聊天消息列表
   */
  messages: Message[];

  /**
   * 更新聊天消息的方法
   */
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;

  /**
   * 获取最新系统消息的回调
   */
  makeSystemMessageCallback: () => TextMessage;

  /**
   * API 请求是否正在进行中
   */
  isLoading: boolean;

  /**
   * 更新 isLoading 状态的方法
   */
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;

  /**
   * 当前 CoAgent 状态列表的引用
   */
  coagentStatesRef: React.RefObject<Record<string, CoagentState>>;

  /**
   * 更新 CoAgent 状态的方法
   */
  setCoagentStatesWithRef: React.Dispatch<React.SetStateAction<Record<string, CoagentState>>>;

  /**
   * 当前代理会话
   */
  agentSession: AgentSession | null;

  /**
   * 更新代理会话的方法
   */
  setAgentSession: React.Dispatch<React.SetStateAction<AgentSession | null>>;

  /**
   * 转发参数
   */
  forwardedParameters?: {
    temperature?: number;
  };

  /**
   * 当前线程 ID
   */
  threadId: string;

  /**
   * 设置当前线程 ID
   */
  setThreadId: (threadId: string) => void;

  /**
   * 当前运行 ID
   */
  runId: string | null;

  /**
   * 设置当前运行 ID
   */
  setRunId: (runId: string | null) => void;

  /**
   * 全局聊天中止控制器
   */
  chatAbortControllerRef: React.MutableRefObject<AbortController | null>;

  /**
   * 代理锁
   */
  agentLock: string | null;

  /**
   * 扩展配置
   */
  extensions: ExtensionsInput;

  /**
   * 更新扩展配置的方法
   */
  setExtensions: React.Dispatch<React.SetStateAction<ExtensionsInput>>;

  /**
   * LangGraph 中断动作
   */
  langGraphInterruptAction: LangGraphInterruptAction | null;

  /**
   * 设置 LangGraph 中断动作
   */
  setLangGraphInterruptAction: (action: Partial<LangGraphInterruptAction>) => void;
};

/**
 * 追加消息的选项
 */
export interface AppendMessageOptions {
  /**
   * 追加消息后是否运行聊天完成，默认为 true
   */
  followUp?: boolean;
}

/**
 * useChat Hook 返回的辅助方法
 */
export type UseChatHelpers = {
  /**
   * 向聊天列表追加用户消息，触发 API 调用获取助手响应
   */
  append: (message: Message, options?: AppendMessageOptions) => Promise<void>;

  /**
   * 重新加载给定聊天历史的最后一个 AI 聊天响应
   */
  reload: (messageId: string) => Promise<void>;

  /**
   * 立即中止当前请求，如果有的话保留生成的令牌
   */
  stop: () => void;

  /**
   * 运行聊天完成
   */
  runChatCompletion: () => Promise<Message[]>;
};

/**
 * 底层聊天 Hook，提供完整的聊天功能实现
 */
export function useChat(options: UseChatOptions): UseChatHelpers {
  const {
    messages,
    setMessages,
    makeSystemMessageCallback,
    copilotConfig,
    setIsLoading,
    initialMessages,
    isLoading,
    actions,
    onFunctionCall,
    onCoAgentStateRender,
    setCoagentStatesWithRef,
    coagentStatesRef,
    agentSession,
    setAgentSession,
    threadId,
    setThreadId,
    runId,
    setRunId,
    chatAbortControllerRef,
    agentLock,
    extensions,
    setExtensions,
    langGraphInterruptAction,
    setLangGraphInterruptAction,
  } = options;

  // 创建 CopilotRuntimeClient 实例
  const runtimeClient = useMemo(() => {
    return new CopilotRuntimeClient({
      url: copilotConfig.chatApiEndpoint,
      publicApiKey: copilotConfig.publicApiKey,
      headers: copilotConfig.headers,
      credentials: copilotConfig.credentials,
    });
  }, [copilotConfig]);

  // 内部引用管理
  const runChatCompletionRef = useRef<(previousMessages: Message[]) => Promise<Message[]>>();
  
  // 保持状态引用，用于 renderAndWait
  const agentSessionRef = useRef<AgentSession | null>(agentSession);
  agentSessionRef.current = agentSession;

  const runIdRef = useRef<string | null>(runId);
  runIdRef.current = runId;
  
  const extensionsRef = useRef<ExtensionsInput>(extensions);
  extensionsRef.current = extensions;

  // 待处理的追加消息队列
  const pendingAppendsRef = useRef<{ message: Message; followUp: boolean }[]>([]);

  // 当前的占位符消息引用
  const currentPlaceholderRef = useRef<TextMessage | null>(null);

  /**
   * 运行聊天完成的核心实现 - 使用 CopilotRuntimeClient 流式传输
   */
  const runChatCompletion = useCallback(
    async (previousMessages: Message[] = messages): Promise<Message[]> => {
      if (isLoading) {
        return previousMessages;
      }

      setIsLoading(true);

      try {
        // 创建占位符消息
        const placeholderMessage = new TextMessage({
          content: "",
          role: "assistant",
        });
        
        currentPlaceholderRef.current = placeholderMessage;
        chatAbortControllerRef.current = new AbortController();

        // 更新消息列表
        setMessages([...previousMessages, placeholderMessage]);

        // 获取系统消息
        const systemMessage = makeSystemMessageCallback();
        const messagesWithContext = [
          systemMessage,
          ...(initialMessages || []),
          ...previousMessages,
        ];

        // 准备请求数据
        const requestData = {
          messages: messagesWithContext,
          actions: actions.map(action => ({
            name: action.name,
            description: action.description || "",
            parameters: action.parameters || [],
            available: "enabled" as const,
          })),
          threadId: threadId,
          agentSession: agentSession ? {
            agentName: agentSession.agentName,
            threadId: agentSession.threadId,
          } : undefined,
          extensions: extensionsRef.current,
          forwardedParameters: options.forwardedParameters || {},
        };

        let accumulatedContent = "";
        let finalMessages: Message[] = [...previousMessages];

        // 处理流式事件的辅助函数
        const handleStreamEvent = (eventType: string, eventData: any, finalMessages: Message[], previousMessages: Message[], placeholderMessage: TextMessage) => {
          switch (eventType) {
            case "session_start":
              // 会话开始，可以更新线程ID等信息
              if (eventData.threadId) {
                setThreadId(eventData.threadId);
              }
              if (eventData.runId) {
                setRunId(eventData.runId);
              }
              console.log("🚀 Session started:", eventData);
              break;
              
            case "session_end":
              // 会话结束
              console.log("🏁 Session ended:", eventData);
              break;
              
            case "text_delta":
              accumulatedContent += eventData.delta || "";
              // 实时更新占位符消息
              const updatedMessage = new TextMessage({
                id: placeholderMessage.id,
                content: accumulatedContent,
                role: "assistant",
              });
              
              // 更新finalMessages以保持同步
              const currentMessageIndex = finalMessages.findIndex(msg => msg.id === placeholderMessage.id);
              if (currentMessageIndex >= 0) {
                finalMessages[currentMessageIndex] = updatedMessage;
              } else {
                finalMessages.push(updatedMessage);
              }
              
              // 实时更新界面
              setMessages([...previousMessages, ...finalMessages]);
              break;
              
            case "action_execution_start":
              const actionStartData = eventData;
              const actionMessage = new ActionExecutionMessage({
                id: actionStartData.actionExecutionId,
                name: actionStartData.actionName || "",
                arguments: {},
                parentMessageId: actionStartData.parentMessageId,
              });
              
              finalMessages.push(actionMessage);
              setMessages([...previousMessages, ...finalMessages]);
              break;
              
            case "action_execution_args":
              const argsData = eventData;
              const existingActionIndex = finalMessages.findIndex(
                msg => msg.isActionExecutionMessage() && msg.id === argsData.actionExecutionId
              );
              
              if (existingActionIndex >= 0) {
                const existingAction = finalMessages[existingActionIndex] as ActionExecutionMessage;
                try {
                  const argsToAdd = typeof argsData.args === "string" ? JSON.parse(argsData.args) : argsData.args;
                  existingAction.arguments = { ...existingAction.arguments, ...argsToAdd };
                } catch {
                  // 如果无法解析，存储为字符串
                  existingAction.arguments.rawArgs = (existingAction.arguments.rawArgs || "") + argsData.args;
                }
                setMessages([...previousMessages, ...finalMessages]);
              }
              break;
              
            case "action_execution_end":
              // 动作执行结束，可能需要执行客户端动作
              const endData = eventData;
              const actionToExecute = finalMessages.find(
                msg => msg.isActionExecutionMessage() && msg.id === endData.actionExecutionId
              ) as ActionExecutionMessage;
              
              if (actionToExecute && onFunctionCall) {
                executeAction({
                  onFunctionCall,
                  previousMessages: [...previousMessages, ...finalMessages],
                  message: actionToExecute,
                  chatAbortControllerRef,
                  onError: (error) => console.error("Action execution error:", error),
                }).then((resultMessage) => {
                  if (resultMessage) {
                    finalMessages.push(resultMessage);
                    setMessages([...previousMessages, ...finalMessages]);
                  }
                }).catch((error) => {
                  console.error("Action execution failed:", error);
                });
              }
              break;
              
            case "action_execution_result":
              // 处理动作执行结果事件
              const resultData = eventData;
              const resultMessage = new ResultMessage({
                id: `result-${resultData.actionExecutionId}`,
                actionExecutionId: resultData.actionExecutionId,
                actionName: resultData.actionName,
                result: resultData.success ? resultData.result : `Error: ${resultData.error}`,
              });
              
              finalMessages.push(resultMessage);
              setMessages([...previousMessages, ...finalMessages]);
              
              if (resultData.success) {
                console.log(`✅ Action '${resultData.actionName}' completed:`, resultData.result);
              } else {
                console.error(`❌ Action '${resultData.actionName}' failed:`, resultData.error);
              }
              break;
              
            case "error":
              // 处理错误事件
              console.error("❌ Stream error:", eventData);
              break;
              
            case "ping":
            case "heartbeat":
              // 心跳事件，保持连接活跃
              console.debug("💓 Heartbeat:", eventType, eventData);
              break;
              
            default:
              console.debug("🔍 Unknown stream event:", eventType, eventData);
              break;
          }
        };

        // 使用 CopilotRuntimeClient 进行流式传输
        const streamResult = await runtimeClient.generateResponse(requestData, true, {
          enableWebSocket: false,
          fallbackToRest: true,
          onMessage: (streamMessage: Message) => {
            try {
              // 检查是否是流式事件伪消息
              const eventType = (streamMessage as any).eventType;
              const eventData = (streamMessage as any).eventData;
              
              if (eventType) {
                // 处理流式事件（SSE 模式）
                handleStreamEvent(eventType, eventData, finalMessages, previousMessages, placeholderMessage);
              } else {
                // 处理完整消息（非 SSE 流式模式）
                finalMessages.push(streamMessage);
                setMessages([...previousMessages, ...finalMessages]);
                
                // 处理特定类型的消息
                if (streamMessage.type === "action_execution" && onFunctionCall) {
                  const actionMessage = streamMessage as ActionExecutionMessage;
                  executeAction({
                    onFunctionCall,
                    previousMessages: [...previousMessages, ...finalMessages],
                    message: actionMessage,
                    chatAbortControllerRef,
                    onError: (error) => console.error("Action execution error:", error),
                  }).then((resultMessage) => {
                    if (resultMessage) {
                      finalMessages.push(resultMessage);
                      setMessages([...previousMessages, ...finalMessages]);
                    }
                  }).catch((error) => {
                    console.error("Action execution failed:", error);
                  });
                } else if (streamMessage.type === "agent_state") {
                  const agentStateMessage = streamMessage as AgentStateMessage;
                  
                  if (agentStateMessage.agentName && agentStateMessage.state) {
                    setCoagentStatesWithRef(prev => ({
                      ...prev,
                      [agentStateMessage.agentName]: {
                        name: agentStateMessage.agentName,
                        state: agentStateMessage.state,
                        running: agentStateMessage.running,
                        threadId: agentStateMessage.threadId,
                        active: agentStateMessage.active,
                      },
                    }));
                  }
                  
                  if (onCoAgentStateRender && agentStateMessage.state) {
                    const renderInfo = agentStateMessage.state.render || agentStateMessage.state;
                    onCoAgentStateRender(renderInfo, agentStateMessage.state);
                  }
                }
              }
            } catch (error) {
              console.error("Error processing stream message:", error);
            }
          },
          onComplete: (completedMessages: Message[]) => {
            // 流式传输完成
            console.log("Stream completed with", completedMessages.length, "messages");
          },
          onError: (error: Error) => {
            console.error("Stream error:", error);
            
            // 移除占位符消息
            setMessages(previousMessages);
            throw error;
          },
        });

        // 处理最终消息 - streamResult 现在是 Message[] 数组
        if (Array.isArray(streamResult) && streamResult.length > 0) {
          // 合并流式消息结果到 finalMessages，避免重复
          const newStreamMessages = streamResult.filter(msg => 
            !finalMessages.find(existing => existing.id === msg.id)
          );
          finalMessages.push(...newStreamMessages);
        } 
        
        // 确保至少有一个响应消息（如果通过回调累积了内容但没有正式消息）
        if (finalMessages.length === 0 && accumulatedContent) {
          const finalMessage = new TextMessage({
            id: placeholderMessage.id,
            content: accumulatedContent,
            role: "assistant",
          });
          finalMessages.push(finalMessage);
        }

        // 确保界面显示最新状态
        const completeFinalMessages = [...previousMessages, ...finalMessages];
        setMessages(completeFinalMessages);
        return finalMessages;

      } catch (error) {
        console.error('Chat completion error:', error);
        
        // 移除占位符消息
        setMessages(previousMessages);
        
        // 如果是中止错误，不重新抛出
        if (error instanceof Error && error.name === 'AbortError') {
          return previousMessages;
        }
        
        throw error;
      } finally {
        setIsLoading(false);
        chatAbortControllerRef.current = null;
        currentPlaceholderRef.current = null;
      }
    },
    [
      messages,
      isLoading,
      setIsLoading,
      setMessages,
      makeSystemMessageCallback,
      initialMessages,
      actions,
      copilotConfig,
      coagentStatesRef,
      threadId,
      options.forwardedParameters,
      runtimeClient,
      onFunctionCall,
      onCoAgentStateRender,
      setCoagentStatesWithRef,
    ]
  );

  // 存储 runChatCompletion 引用
  runChatCompletionRef.current = runChatCompletion;

  // 处理待处理的消息队列
  React.useEffect(() => {
    if (!isLoading && pendingAppendsRef.current.length > 0) {
      const pending = pendingAppendsRef.current.splice(0);
      const followUp = pending.some((p) => p.followUp);
      const newMessages = [...messages, ...pending.map((p) => p.message)];
      setMessages(newMessages);
      if (followUp) {
        runChatCompletion(newMessages);
      }
    }
  }, [isLoading, messages, setMessages, runChatCompletion]);

  /**
   * 追加消息
   */
  const append = useCallback(
    async (message: Message, options: AppendMessageOptions = {}) => {
      const { followUp = true } = options;

      // 如果正在加载，添加到待处理队列
      if (isLoading) {
        pendingAppendsRef.current.push({ message, followUp });
        return;
      }

      // 立即更新消息列表
      const updatedMessages = [...messages, message];
      setMessages(updatedMessages);

      // 如果需要跟进，运行聊天完成
      if (followUp) {
        await runChatCompletion(updatedMessages);
      }
    },
    [messages, setMessages, isLoading, runChatCompletion]
  );

  /**
   * 重新加载最后一个消息
   */
  const reload = useCallback(
    async (messageId: string) => {
      const messageIndex = messages.findIndex(m => m.id === messageId);
      if (messageIndex === -1) return;

      // 移除从指定消息开始的所有后续消息
      const previousMessages = messages.slice(0, messageIndex);
      setMessages(previousMessages);

      await runChatCompletion(previousMessages);
    },
    [messages, setMessages, runChatCompletion]
  );

  /**
   * 停止当前请求
   */
  const stop = useCallback(() => {
    if (chatAbortControllerRef.current) {
      chatAbortControllerRef.current.abort();
      chatAbortControllerRef.current = null;
    }
    setIsLoading(false);
  }, [setIsLoading]);

  return {
    append,
    reload,
    stop,
    runChatCompletion,
  };
}

/**
 * 执行前端动作
 */
export async function executeAction({
  onFunctionCall,
  previousMessages,
  message,
  chatAbortControllerRef,
  onError,
}: {
  onFunctionCall: FunctionCallHandler;
  previousMessages: Message[];
  message: ActionExecutionMessage;
  chatAbortControllerRef: React.MutableRefObject<AbortController | null>;
  onError: (error: Error) => void;
}) {
  try {
    const result = await onFunctionCall(message);
    return result;
  } catch (error) {
    onError(error as Error);
    throw error;
  }
}

/**
 * 根据动作名称查找对应的前端动作
 */
export function getPairedFeAction(
  actions: FrontendAction<any>[],
  message: ActionExecutionMessage | ResultMessage,
) {
  if (message.type === "action_execution") {
    return actions.find(action => action.name === message.name);
  } else if (message.type === "result") {
    return actions.find(action => action.name === message.actionName);
  }
  return undefined;
}

/**
 * 构造最终消息列表
 */
export function constructFinalMessages(
  syncedMessages: Message[],
  previousMessages: Message[],
  newMessages: Message[],
): Message[] {
  // 合并消息并去重
  const allMessages = [...previousMessages, ...syncedMessages, ...newMessages];
  const uniqueMessages = allMessages.reduce((acc, message) => {
    if (!acc.find(m => m.id === message.id)) {
      acc.push(message);
    }
    return acc;
  }, [] as Message[]);
  
  return uniqueMessages;
} 