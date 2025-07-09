import React, { useCallback, useRef } from "react";
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

  /**
   * 运行聊天完成的核心实现
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
          messages: messagesWithContext.map(msg => msg.toJSON()),
          actions: actions.map(action => ({
            name: action.name,
            description: action.description,
            parameters: action.parameters,
          })),
          threadId: threadId,
          runId: runIdRef.current,
          extensions: extensionsRef.current,
          agentStates: Object.values(coagentStatesRef.current || {}).map((state) => ({
            agentName: state.name,
            state: JSON.stringify(state.state),
          })),
          forwardedParameters: options.forwardedParameters || {},
        };

        // 获取公共 API 密钥和请求头
        const publicApiKey = copilotConfig.publicApiKey;
        const headers = {
          'Content-Type': 'application/json',
          ...(copilotConfig.headers || {}),
          ...(publicApiKey ? { "X-Copilot-Public-Api-Key": publicApiKey } : {}),
        };

        // 发送请求
        const response = await fetch(copilotConfig.chatApiEndpoint, {
          method: 'POST',
          headers,
          body: JSON.stringify(requestData),
          signal: chatAbortControllerRef.current.signal,
          credentials: copilotConfig.credentials,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        let finalMessages: Message[] = [...previousMessages];
        let accumulatedContent = "";

        // 处理响应
        if (response.body) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();

          try {
            while (true) {
              const { done, value } = await reader.read();
              
              if (done) break;

              const chunk = decoder.decode(value, { stream: true });
              accumulatedContent += chunk;

              // 更新消息内容
              const updatedMessage = new TextMessage({
                id: placeholderMessage.id,
                content: accumulatedContent,
                role: "assistant",
              });

              setMessages([...previousMessages, updatedMessage]);
            }
          } finally {
            reader.releaseLock();
          }
        } else {
          // 非流式响应
          const responseData = await response.json();
          if (responseData.content) {
            accumulatedContent = responseData.content;
          }
        }

        // 最终消息
        if (accumulatedContent) {
          const finalMessage = new TextMessage({
            id: placeholderMessage.id,
            content: accumulatedContent,
            role: "assistant",
          });
          finalMessages = [...previousMessages, finalMessage];
        }

        setMessages(finalMessages);
        return finalMessages;

      } catch (error) {
        console.error('Chat completion error:', error);
        
        // 移除占位符消息
        setMessages(previousMessages);
        
        throw error;
      } finally {
        setIsLoading(false);
        chatAbortControllerRef.current = null;
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
    ]
  );

  // 存储 runChatCompletion 引用
  runChatCompletionRef.current = runChatCompletion;

  /**
   * 追加消息
   */
  const append = useCallback(
    async (message: Message, options: AppendMessageOptions = {}) => {
      const { followUp = true } = options;

      // 添加到待处理队列
      pendingAppendsRef.current.push({ message, followUp });

      // 如果当前没有正在进行的请求，开始处理
      if (!isLoading) {
        const updatedMessages = [...messages, message];
        setMessages(updatedMessages);

        if (followUp) {
          await runChatCompletion(updatedMessages);
        }

        // 处理队列中的其他消息
        while (pendingAppendsRef.current.length > 0) {
          const pending = pendingAppendsRef.current.shift();
          if (pending && pending.followUp) {
            await runChatCompletion();
          }
        }
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