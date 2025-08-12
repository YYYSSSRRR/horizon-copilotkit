import React, { useCallback, useRef, useMemo, useEffect } from "react";
import { randomId } from "@copilotkit/shared";
import { 
  Message, 
  TextMessage, 
  ActionExecutionMessage, 
  ResultMessage, 
  AgentStateMessage 
} from "../client/message-types";
import { FrontendAction, ScriptAction } from "../types/frontend-action";
import { CoAgentStateRender } from "../types/coagent-action";
import { CoagentState } from "../types/coagent-state";
import { CopilotRuntimeClient } from "../client/copilot-runtime-client";

// Utility function to handle incomplete JSON (similar to untruncate-json)
function parsePartialJson(jsonStr: string): any {
  try {
    return JSON.parse(jsonStr);
  } catch (e) {
    // Try to fix common truncation issues
    let fixedStr = jsonStr;
    
    // If the string ends with incomplete object or array, try to close it
    if (fixedStr.endsWith(',')) {
      fixedStr = fixedStr.slice(0, -1);
    }
    
    // Count braces and brackets to close them properly
    let openBraces = 0;
    let openBrackets = 0;
    
    for (const char of fixedStr) {
      if (char === '{') openBraces++;
      else if (char === '}') openBraces--;
      else if (char === '[') openBrackets++;
      else if (char === ']') openBrackets--;
    }
    
    // Close unclosed braces and brackets
    while (openBraces > 0) {
      fixedStr += '}';
      openBraces--;
    }
    while (openBrackets > 0) {
      fixedStr += ']';
      openBrackets--;
    }
    
    try {
      return JSON.parse(fixedStr);
    } catch (e2) {
      // If still can't parse, return null to indicate incomplete
      return null;
    }
  }
}

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
   * 发送到 API 的脚本动作列表
   */
  scriptActions?: ScriptAction<any>[];

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
    scriptActions = [],
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
    async (previousMessages: Message[] = messages, isFollowUp: boolean = false): Promise<Message[]> => {

      if (isLoading) {
        return previousMessages;
      }

      setIsLoading(true);

      try {
        // 为流式内容生成唯一 ID
        const streamingMessageId = randomId();
        
        chatAbortControllerRef.current = new AbortController();

        // 保持原有消息列表
        setMessages([...previousMessages]);

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
          actions: [
            // 常规 actions
            ...actions.map(action => ({
              name: action.name,
              description: action.description || "",
              parameters: action.parameters || [],
              available: "enabled" as const,
            })),
            // scriptActions 转换为 actions 格式
            ...scriptActions.map(scriptAction => ({
              name: scriptAction.name,
              description: scriptAction.description || "",
              parameters: scriptAction.parameters || [],
              available: "enabled" as const,
            }))
          ],
          threadId: threadId,
          agentSession: agentSession ? {
            agentName: agentSession.agentName,
            threadId: agentSession.threadId,
          } : undefined,
          extensions: extensionsRef.current,
          forwardedParameters: options.forwardedParameters || {},
        };

        let accumulatedContent = "";
        let finalMessages: Message[] = [];
        let syncedMessages: Message[] = [];
        let newMessages: Message[] = [];

        // 处理流式事件的辅助函数
        const handleStreamEvent = (eventType: string, eventData: any, streamingMsgId: string) => {
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
              
            case "text_content":
              // 处理累加内容（匹配 TypeScript 版本的行为）
              const cumulativeContent = eventData.content || "";
              const cumulativeMessage = new TextMessage({
                id: streamingMsgId,
                content: cumulativeContent,
                role: "assistant",
              });
              
              // 更新newMessages
              const cumulativeMessageIndex = newMessages.findIndex(msg => msg.id === streamingMsgId);
              if (cumulativeMessageIndex >= 0) {
                newMessages[cumulativeMessageIndex] = cumulativeMessage;
              } else {
                newMessages.push(cumulativeMessage);
              }
              
              // 构造最终消息列表并实时更新界面
              finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
              setMessages(finalMessages);

              if (isFollowUp) {
                setIsLoading(false);
              }
              break;
              
            case "text_end":
              // 文本消息结束，标记为成功状态
              const endMessageIndex = newMessages.findIndex(msg => msg.id === streamingMsgId);
              if (endMessageIndex >= 0) {
                newMessages[endMessageIndex].status = { code: "success" };
                finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
                setMessages(finalMessages);
              }
              console.log("📝 Text message completed:", eventData);
              break;
              
            case "action_execution_start":
              const actionStartData = eventData;
              const actionMessage = new ActionExecutionMessage({
                id: actionStartData.actionExecutionId,
                name: actionStartData.actionName || "",
                arguments: { __rawArgs: "" }, // 初始化参数累积容器
                parentMessageId: actionStartData.parentMessageId,
              });
              
              newMessages.push(actionMessage);
              finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
              setMessages(finalMessages);
              break;
              
            case "action_execution_args":
              const argsData = eventData;
              const existingActionIndex = newMessages.findIndex(
                msg => msg.isActionExecutionMessage() && msg.id === argsData.actionExecutionId
              );
              
              if (existingActionIndex >= 0) {
                const existingAction = newMessages[existingActionIndex] as ActionExecutionMessage;
                
                // 确保 arguments 对象存在
                if (!existingAction.arguments) {
                  existingAction.arguments = {};
                }
                
                // 累积参数字符串片段，类似 GraphQL 版本的处理方式
                if (typeof existingAction.arguments.__rawArgs !== 'string') {
                  existingAction.arguments.__rawArgs = "";
                }
                existingAction.arguments.__rawArgs += argsData.args || "";
                
                // 尝试解析累积的参数字符串，使用改进的 JSON 解析
                const parsedArgs = parsePartialJson(existingAction.arguments.__rawArgs);
                if (parsedArgs !== null) {
                  // 解析成功，用解析后的参数替换原参数，但保留 __rawArgs 用于调试
                  const { __rawArgs, ...cleanArgs } = parsedArgs;
                  existingAction.arguments = {
                    ...cleanArgs,
                    __rawArgs: existingAction.arguments.__rawArgs // 保留原始字符串用于调试
                  };
                }
                // 如果解析失败（parsedArgs === null），继续累积
                
                finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
                setMessages(finalMessages);
              }
              break;
              
            case "action_execution_end":
              // 动作执行结束，确保参数完整但不在这里执行客户端动作
              const endData = eventData;
              const actionToExecute = newMessages.find(
                msg => msg.isActionExecutionMessage() && msg.id === endData.actionExecutionId
              ) as ActionExecutionMessage;
              
              if (actionToExecute) {
                // 确保在结束时参数被正确解析
                if (actionToExecute.arguments && actionToExecute.arguments.__rawArgs) {
                  const finalParsedArgs = parsePartialJson(actionToExecute.arguments.__rawArgs);
                  if (finalParsedArgs !== null) {
                    const { __rawArgs, ...cleanArgs } = finalParsedArgs;
                    actionToExecute.arguments = cleanArgs;
                  }
                }
                
                // 只更新消息状态，不执行动作（等待流式传输完成后统一执行）
                finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
                setMessages(finalMessages);
              }
              console.log("📝 Action execution ended:", endData);
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
              
              newMessages.push(resultMessage);
              finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
              setMessages(finalMessages);
              
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
          onMessage: (streamMessage: Message) => {
            try {
              // 检查是否是流式事件伪消息
              const eventType = (streamMessage as any).eventType;
              const eventData = (streamMessage as any).eventData;
              
              if (eventType) {
                // 处理流式事件（SSE 模式）
                handleStreamEvent(eventType, eventData, streamingMessageId);
              } else {
                // 处理完整消息（非 SSE 流式模式）
                newMessages.push(streamMessage);
                finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);
                setMessages(finalMessages);
                
                // 处理特定类型的消息
                if (streamMessage.type === "agent_state") {
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
            // 🔧 修复：流式传输完成时，如果不是后续请求且没有需要执行的动作，可以提前设置 loading 为 false
            // 这样可以避免等到 finally 块才设置，提升用户体验
            console.log("🏁 Stream completed with", completedMessages.length, "messages");
          },
          onError: (error: Error) => {
            console.error("Stream error:", error);
            
            // 移除占位符消息
            setMessages(previousMessages);
            throw error;
          },
        });

        // 处理最终消息 - streamResult 现在是 Message[] 数组
        // 注意：由于流式事件在 StreamProcessor 中已经通过回调处理，streamResult 可能为空
        // 真正的消息应该已经通过 handleStreamEvent 累积在 finalMessages 中
        if (Array.isArray(streamResult) && streamResult.length > 0) {
          // 过滤掉流式事件伪消息，只保留真正的消息
          const realMessages = streamResult.filter(msg => {
            // 检查是否是流式事件伪消息
            const hasEventType = (msg as any).eventType;
            const hasEventData = (msg as any).eventData;
            
            // 如果有 eventType 和 eventData，说明是伪消息，应该过滤掉
            if (hasEventType && hasEventData) {
              return false;
            }
            
            // 过滤掉空内容的 TextMessage（可能是事件残留或占位符消息）
            if (msg.type === "text" && (!((msg as TextMessage).content) || (msg as TextMessage).content === "")) {
              return false;
            }
            
            return true;
          });
          
          // 合并真正的消息到 newMessages，避免重复
          const newStreamMessages = realMessages.filter(msg => 
            !newMessages.find(existing => existing.id === msg.id)
          );
          newMessages.push(...newStreamMessages);
        } 
        
        // 确保至少有一个响应消息（如果通过回调累积了内容但没有正式消息）
        if (newMessages.length === 0 && accumulatedContent) {
          const finalMessage = new TextMessage({
            id: streamingMessageId,
            content: accumulatedContent,
            role: "assistant",
          });
          newMessages.push(finalMessage);
        }

        // 构造最终消息列表
        finalMessages = constructFinalMessages(syncedMessages, previousMessages, newMessages);

        // 将所有消息状态更新为 success（流式传输完成）
        finalMessages.forEach(msg => {
          if (msg.status.code === "pending") {
            msg.status = { code: "success" };
          }
        });
        
        // 🔧 提前检查：如果流式内容已完成且没有需要执行的动作，可以提前设置 loading 为 false
        // 避免在有内容显示时仍然显示 loading 状态
        const hasCompletedContent = newMessages.some(msg => 
          msg.type === "text" && msg.content && msg.status.code === "success"
        );
        if (hasCompletedContent && !isFollowUp) {
          console.log("📝 Content completed, checking if can set loading to false early");
        }
        
        
        // 确保界面显示最新状态
        // finalMessages 已经包含了 previousMessages，不需要再次合并
        setMessages(finalMessages);
        
        // 执行前端动作（类似 react-core 行为，在流式传输完成后）
        let didExecuteAction = false;
        
        if (onFunctionCall && finalMessages.length > 0) {
          // 找到连续的需要执行的动作消息（从末尾开始）
          const lastMessages = [];
          
          for (let i = finalMessages.length - 1; i >= 0; i--) {
            const message = finalMessages[i];
            if (
              (message.isActionExecutionMessage() || message.isResultMessage()) &&
              message.status.code !== "pending"
            ) {
              lastMessages.unshift(message);
            } else if (!message.isAgentStateMessage()) {
              break;
            }
          }
          
          // 同步执行动作（类似 react-core 的行为）
          for (const message of lastMessages) {
            // 先更新UI状态，显示当前消息
            setMessages(finalMessages);
            
            // 查找对应的前端动作
            const action = findAction(
              (message as ActionExecutionMessage).name, 
              actions, 
              scriptActions
            );
            
            // 只有找到对应的前端动作才执行（react-core 的行为）
            if (action && message.isActionExecutionMessage()) {
              try {
                const resultMessage = await executeAction({
                  onFunctionCall,
                  message: message as ActionExecutionMessage,
                  onError: (error) => console.error("Action execution error:", error),
                });
                
                if (resultMessage) {
                  didExecuteAction = true;
                  // 找到消息在 finalMessages 中的位置，并插入结果消息
                  const messageIndex = finalMessages.findIndex(msg => msg.id === message.id);
                  if (messageIndex !== -1) {
                    finalMessages.splice(messageIndex + 1, 0, resultMessage);
                  }
                }
              } catch (error) {
                console.error("Action execution failed:", error);
              }
            } else if (message.isActionExecutionMessage()) {
              // 如果找不到对应的前端动作，说明这是后端动作，跳过执行
              console.log(`Skipping backend action: ${(message as ActionExecutionMessage).name}`);
            }
          }
          
          // 最终更新消息状态
          setMessages(finalMessages);
        }
        
        // 检查是否需要后续请求（类似 react-core 行为）
        // 对于后端动作，我们也需要触发后续请求，因为后端可能返回需要处理的结果
        const hasBackendActions = finalMessages.some((msg: Message) => {
          if (!msg.isActionExecutionMessage()) return false;
          const actionMsg = msg as ActionExecutionMessage;
          // 检查是否既不在 actions 中也不在 scriptActions 中（即为后端动作）
          const foundAction = findAction(actionMsg.name, actions, scriptActions);
          return !foundAction;
        });
        
        if (
          !isFollowUp && // 只有非后续请求才能触发后续请求，避免死循环
          (didExecuteAction || hasBackendActions) && // 前端动作执行或存在后端动作时都需要后续请求
          !chatAbortControllerRef.current?.signal.aborted
        ) {
          console.log("🔄 Executed action in this run, triggering follow-up completion...");
          
          // 等待一个 tick 确保 React 状态更新完成
          await new Promise((resolve) => setTimeout(resolve, 10));
          
          // 🔑 关键：传递完整的消息列表，不是之前的 previousMessages
          // 这样避免了重复，与 react-core 行为一致
          const followUpMessages = await runChatCompletion(finalMessages, true);
          return followUpMessages;
        }
        
        return newMessages;

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
        // 确保 loading 状态被设置为 false（可能已经在流式处理中设置过了）
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
        runChatCompletion(newMessages, false); // 明确标记为非后续请求
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
        await runChatCompletion(updatedMessages, false); // 明确标记为非后续请求
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

      await runChatCompletion(previousMessages, false); // 明确标记为非后续请求
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
 * 创建函数调用处理器
 */
export function createFunctionCallHandler(
  actions: FrontendAction<any>[], 
  scriptActions: ScriptAction<any>[] = []
): FunctionCallHandler {
  return async (message: ActionExecutionMessage): Promise<ResultMessage | void> => {
    // 使用 findAction 方法查找动作
    const action = findAction(message.name, actions, scriptActions);
    
    if (!action) {
      // 如果在两个地方都找不到对应的动作，说明这是后端动作，直接返回 void 而不是抛出异常
      console.log(`Skipping backend action in function call handler: ${message.name}`);
      return;
    }
    
    try {
      if (!action.handler) {
        throw new Error(`Action ${message.name} has no handler function`);
      }
      
      const result = await action.handler(message.arguments);
      
      return new ResultMessage({
        id: `result-${message.id}`,
        actionExecutionId: message.id,
        actionName: message.name,
        result: typeof result === 'string' ? result : JSON.stringify(result),
      });
    } catch (error) {
      return new ResultMessage({
        id: `result-${message.id}`,
        actionExecutionId: message.id,
        actionName: message.name,
        result: `Error: ${error instanceof Error ? error.message : String(error)}`,
      });
    }
  };
}

async function executeAction({
  onFunctionCall,
  message,
  onError,
}: {
  onFunctionCall: FunctionCallHandler;
  message: ActionExecutionMessage;
  onError: (error: Error) => void;
}) {
  try {
    const result = await onFunctionCall(message);
    // 如果 onFunctionCall 返回 void，说明是后端动作，应该跳过
    return result;
  } catch (error) {
    onError(error as Error);
    throw error;
  }
}

/**
 * 根据动作名称在 actions 和 scriptActions 中查找动作
 */
export function findAction(
  actionName: string,
  actions: FrontendAction<any>[],
  scriptActions?: ScriptAction<any>[]
): FrontendAction<any> | ScriptAction<any> | undefined {
  // 首先在常规 actions 中查找
  let foundAction = actions.find(action => action.name === actionName);
  
  // 如果没找到，在 scriptActions 中查找
  if (!foundAction && scriptActions) {
    foundAction = scriptActions.find(action => action.name === actionName);
  }
  
  return foundAction;
}

/**
 * 根据动作名称查找对应的前端动作
 */
export function getPairedFeAction(
  actions: FrontendAction<any>[],
  message: ActionExecutionMessage | ResultMessage,
  scriptActions?: ScriptAction<any>[]
) {
  let actionName: string;
  
  if (message.type === "action_execution") {
    actionName = message.name;
  } else if (message.type === "result") {
    actionName = message.actionName;
  } else {
    return undefined;
  }
  
  return findAction(actionName, actions, scriptActions);
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