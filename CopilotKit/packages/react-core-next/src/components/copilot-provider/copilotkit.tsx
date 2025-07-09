import React, { ReactNode, useMemo, useState, useCallback, useEffect } from "react";
import { randomId } from "@copilotkit/shared";
import { CopilotContextProvider, CopilotContextValue, CopilotReadable } from "../../context/copilot-context";
import { MessagesContextProvider, MessagesContextValue } from "../../context/messages-context";
import { createCopilotRuntimeClient, CopilotRuntimeClient } from "../../client";
import { FrontendAction } from "../../types/frontend-action";
import { CopilotChatSuggestionConfiguration } from "../../types/chat-suggestion-configuration";
import { DocumentPointer } from "../../types/document-pointer";
import { CoAgentStateRender } from "../../types/coagent-action";
import { SystemMessageFunction } from "../../types/system-message";
import { 
  Message, 
  TextMessage, 
  ActionExecutionMessage, 
  ResultMessage, 
  AgentStateMessage 
} from "../../client";
import { shouldShowDevConsole } from "../../utils";
import { ToastProvider } from "../toast/toast-provider";
import { CopilotErrorBoundary } from "../error-boundary/error-boundary";

export interface CopilotKitProps {
  /**
   *  Your Copilot Cloud API key. Don't have it yet? Go to https://cloud.copilotkit.ai and get one for free.
   */
  publicApiKey?: string;

  /**
   * Restrict input to a specific topic.
   * @deprecated Use `guardrails_c` instead to control input restrictions
   */
  cloudRestrictToTopic?: {
    validTopics?: string[];
    invalidTopics?: string[];
  };

  /**
   * Restrict input to specific topics using guardrails.
   * @remarks
   *
   * This feature is only available when using CopilotKit's hosted cloud service. To use this feature, sign up at https://cloud.copilotkit.ai to get your publicApiKey. The feature allows restricting chat conversations to specific topics.
   */
  guardrails_c?: {
    validTopics?: string[];
    invalidTopics?: string[];
  };

  /**
   * The endpoint for the Copilot Runtime instance. [Click here for more information](/concepts/copilot-runtime).
   */
  runtimeUrl?: string;

  /**
   * The endpoint for the Copilot transcribe audio service.
   */
  transcribeAudioUrl?: string;

  /**
   * The endpoint for the Copilot text to speech service.
   */
  textToSpeechUrl?: string;

  /**
   * Additional headers to be sent with the request.
   *
   * For example:
   * ```json
   * {
   *   "Authorization": "Bearer X"
   * }
   * ```
   */
  headers?: Record<string, string>;

  /**
   * The children to be rendered within the CopilotKit.
   */
  children: ReactNode;

  /**
   * Custom properties to be sent with the request
   * For example:
   * ```js
   * {
   *   'user_id': 'users_id',
   * }
   * ```
   */
  properties?: Record<string, any>;

  /**
   * Indicates whether the user agent should send or receive cookies from the other domain
   * in the case of cross-origin requests.
   */
  credentials?: RequestCredentials;

  /**
   * Whether to show the dev console.
   *
   * If set to "auto", the dev console will be show on localhost only.
   */
  showDevConsole?: boolean | "auto";

  /**
   * The name of the agent to use.
   */
  agent?: string;

  /**
   * The forwarded parameters to use for the task.
   */
  forwardedParameters?: {
    temperature?: number;
  };

  /**
   * The auth config to use for the CopilotKit.
   * @remarks
   *
   * This feature is only available when using CopilotKit's hosted cloud service. To use this feature, sign up at https://cloud.copilotkit.ai to get your publicApiKey. The feature allows restricting chat conversations to specific topics.
   */
  authConfig_c?: {
    SignInComponent: React.ComponentType<{
      onSignInComplete: (authState: any) => void;
    }>;
  };

  /**
   * The thread id to use for the CopilotKit.
   */
  threadId?: string;
}

export function CopilotKit({
  children,
  publicApiKey,
  cloudRestrictToTopic,
  guardrails_c,
  runtimeUrl,
  transcribeAudioUrl,
  textToSpeechUrl,
  headers,
  properties,
  credentials,
  showDevConsole = "auto",
  agent,
  forwardedParameters,
  authConfig_c,
  threadId: initialThreadId,
}: CopilotKitProps) {
  // 默认 runtimeUrl 如果未提供
  const defaultRuntimeUrl = useMemo(() => 
    runtimeUrl || (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}/api/copilotkit` : ''),
    [runtimeUrl]
  );

  // 缓存运行时客户端配置对象
  const runtimeClientConfig = useMemo(() => ({
    url: defaultRuntimeUrl,
    publicApiKey,
    headers,
    credentials,
    properties,
  }), [defaultRuntimeUrl, publicApiKey, headers, credentials, properties]);

  // 运行时客户端
  const runtimeClient = useMemo(() => {
    return createCopilotRuntimeClient(runtimeClientConfig);
  }, [runtimeClientConfig]);

  // 核心状态管理
  const [actions, setActionsState] = useState<Record<string, FrontendAction>>({});
  const [readables, setReadablesState] = useState<Record<string, CopilotReadable>>({});
  const [chatSuggestions, setChatSuggestionsState] = useState<Record<string, CopilotChatSuggestionConfiguration>>({});
  const [documentPointers, setDocumentPointersState] = useState<Record<string, DocumentPointer>>({});
  const [coAgentStateRenders, setCoAgentStateRendersState] = useState<Record<string, CoAgentStateRender>>({});
  const [currentSystemMessage, setCurrentSystemMessage] = useState<SystemMessageFunction | undefined>(undefined);

  // 消息相关状态
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string>(initialThreadId || randomId());

  // 动作管理
  const setAction = useCallback((id: string, actionDef: FrontendAction) => {
    setActionsState(prev => ({ ...prev, [id]: actionDef }));
  }, []);

  const removeAction = useCallback((id: string) => {
    setActionsState(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // 可读上下文管理
  const setReadable = useCallback((id: string, readable: CopilotReadable) => {
    setReadablesState(prev => ({ ...prev, [id]: readable }));
  }, []);

  const removeReadable = useCallback((id: string) => {
    setReadablesState(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // 聊天建议管理
  const setChatSuggestion = useCallback((id: string, suggestion: CopilotChatSuggestionConfiguration) => {
    setChatSuggestionsState(prev => ({ ...prev, [id]: suggestion }));
  }, []);

  const removeChatSuggestion = useCallback((id: string) => {
    setChatSuggestionsState(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // 文档指针管理
  const setDocumentPointer = useCallback((id: string, pointer: DocumentPointer) => {
    setDocumentPointersState(prev => ({ ...prev, [id]: pointer }));
  }, []);

  const removeDocumentPointer = useCallback((id: string) => {
    setDocumentPointersState(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // CoAgent 状态渲染器管理
  const setCoAgentStateRender = useCallback((id: string, render: CoAgentStateRender) => {
    setCoAgentStateRendersState(prev => ({ ...prev, [id]: render }));
  }, []);

  const removeCoAgentStateRender = useCallback((id: string) => {
    setCoAgentStateRendersState(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // 获取上下文字符串
  const getContextString = useCallback((categories?: string[]) => {
    const relevantReadables = Object.values(readables).filter(readable => {
      if (!categories) return true;
      return readable.categories?.some(cat => categories.includes(cat));
    });

    return relevantReadables
      .map(readable => {
        const value = readable.convert ? readable.convert(readable.value) : String(readable.value);
        return `${readable.description}: ${value}`;
      })
      .join("\n");
  }, [readables]);

  // 获取 CoAgent 状态渲染器
  const getCoAgentStateRender = useCallback((agentName: string, nodeName?: string) => {
    return Object.values(coAgentStateRenders).find(render => {
      return render.name === agentName && (!nodeName || render.nodeName === nodeName);
    });
  }, [coAgentStateRenders]);

  // 消息管理
  const appendMessage = useCallback((message: Message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const deleteMessage = useCallback((messageId: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
  }, []);

  const reloadMessages = useCallback(() => {
    // 重新加载消息的逻辑
    setMessages([]);
  }, []);

  const stopMessage = useCallback((messageId: string) => {
    // 停止特定消息生成的逻辑
    if (runtimeClient) {
      runtimeClient.abort();
    }
  }, [runtimeClient]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // 便捷消息创建方法
  const appendTextMessage = useCallback((content: string, role: "user" | "assistant" | "system" = "user") => {
    const message = new TextMessage({ content, role });
    appendMessage(message);
  }, [appendMessage]);

  const appendActionMessage = useCallback((name: string, args: Record<string, any>) => {
    const message = new ActionExecutionMessage({ name, arguments: args });
    appendMessage(message);
  }, [appendMessage]);

  const appendResultMessage = useCallback((actionExecutionId: string, actionName: string, result: any) => {
    const message = new ResultMessage({ actionExecutionId, actionName, result });
    appendMessage(message);
  }, [appendMessage]);

  const appendAgentStateMessage = useCallback((agentName: string, state: any, running: boolean, threadId: string, active: boolean) => {
    const message = new AgentStateMessage({ agentName, state, running, threadId, active });
    appendMessage(message);
  }, [appendMessage]);

  // 消息查询方法
  const getTextMessages = useCallback(() => {
    return messages.filter(msg => msg.isTextMessage()) as TextMessage[];
  }, [messages]);

  const getActionMessages = useCallback(() => {
    return messages.filter(msg => msg.isActionExecutionMessage()) as ActionExecutionMessage[];
  }, [messages]);

  const getResultMessages = useCallback(() => {
    return messages.filter(msg => msg.isResultMessage()) as ResultMessage[];
  }, [messages]);

  const getAgentStateMessages = useCallback(() => {
    return messages.filter(msg => msg.isAgentStateMessage()) as AgentStateMessage[];
  }, [messages]);

  const getMessageById = useCallback((messageId: string) => {
    return messages.find(msg => msg.id === messageId);
  }, [messages]);

  const getMessagesByParentId = useCallback((parentId: string) => {
    return messages.filter(msg => 
      (msg.isTextMessage() || msg.isActionExecutionMessage() || msg.isImageMessage()) && 
      msg.parentMessageId === parentId
    );
  }, [messages]);

  // 缓存数组和对象以避免无限循环
  const actionsArray = useMemo(() => Object.values(actions), [actions]);
  const chatSuggestionsArray = useMemo(() => Object.values(chatSuggestions), [chatSuggestions]);
  const documentPointersArray = useMemo(() => Object.values(documentPointers), [documentPointers]);
  const cloudConfig = useMemo(() => ({ guardrails: guardrails_c }), [guardrails_c]);
  const authStatesConfig = useMemo(() => ({}), []);

  // 缓存占位符函数
  const setSystemMessagePlaceholder = useCallback(() => {}, []);
  const setRunIdPlaceholder = useCallback(() => {}, []);
  const setLangGraphInterruptActionPlaceholder = useCallback(() => {}, []);
  const removeLangGraphInterruptActionPlaceholder = useCallback(() => {}, []);
  const setAgentSessionPlaceholder = useCallback(() => {}, []);
  const setAuthStatesCPlaceholder = useCallback(() => {}, []);

  // 构建上下文值
  const copilotContextValue: CopilotContextValue = useMemo(() => ({
    runtimeClient,
    actions: actionsArray,
    setAction,
    removeAction,
    readables,
    setReadable,
    removeReadable,
    chatSuggestions: chatSuggestionsArray,
    setChatSuggestion,
    removeChatSuggestion,
    documentPointers: documentPointersArray,
    setDocumentPointer,
    removeDocumentPointer,
    coAgentStateRenders,
    setCoAgentStateRender,
    removeCoAgentStateRender,
    systemMessage: undefined, // 系统消息通过 props 处理
    setSystemMessage: setSystemMessagePlaceholder,
    chatInstructions: undefined, // 聊天指令
    forwardedParameters: forwardedParameters,
    isLoading,
    setIsLoading,
    threadId,
    setThreadId,
    runId: null,
    setRunId: setRunIdPlaceholder,
    langGraphInterruptAction: undefined,
    setLangGraphInterruptAction: setLangGraphInterruptActionPlaceholder,
    removeLangGraphInterruptAction: removeLangGraphInterruptActionPlaceholder,
    agentSession: null,
    setAgentSession: setAgentSessionPlaceholder,
    authConfig_c: authConfig_c,
    authStates_c: authStatesConfig,
    setAuthStates_c: setAuthStatesCPlaceholder,
    cloud: cloudConfig,
    getContextString,
    getCoAgentStateRender,
  }), [
    runtimeClient,
    actionsArray,
    setAction,
    removeAction,
    readables,
    setReadable,
    removeReadable,
    chatSuggestionsArray,
    setChatSuggestion,
    removeChatSuggestion,
    documentPointersArray,
    setDocumentPointer,
    removeDocumentPointer,
    coAgentStateRenders,
    setCoAgentStateRender,
    removeCoAgentStateRender,
    forwardedParameters,
    isLoading,
    setIsLoading,
    threadId,
    setThreadId,
    authConfig_c,
    authStatesConfig,
    cloudConfig,
    getContextString,
    getCoAgentStateRender,
    setSystemMessagePlaceholder,
    setRunIdPlaceholder,
    setLangGraphInterruptActionPlaceholder,
    removeLangGraphInterruptActionPlaceholder,
    setAgentSessionPlaceholder,
    setAuthStatesCPlaceholder,
  ]);

  const messagesContextValue: MessagesContextValue = useMemo(() => ({
    messages,
    setMessages,
    appendMessage,
    deleteMessage,
    reloadMessages,
    stopMessage,
    isLoading,
    setIsLoading,
    threadId,
    setThreadId,
    appendTextMessage,
    appendActionMessage,
    appendResultMessage,
    appendAgentStateMessage,
    getTextMessages,
    getActionMessages,
    getResultMessages,
    getAgentStateMessages,
    getMessageById,
    getMessagesByParentId,
    clearMessages,
  }), [
    messages,
    setMessages,
    appendMessage,
    deleteMessage,
    reloadMessages,
    stopMessage,
    isLoading,
    setIsLoading,
    threadId,
    setThreadId,
    appendTextMessage,
    appendActionMessage,
    appendResultMessage,
    appendAgentStateMessage,
    getTextMessages,
    getActionMessages,
    getResultMessages,
    getAgentStateMessages,
    getMessageById,
    getMessagesByParentId,
    clearMessages,
  ]);

  // 开发控制台
  const showDevConsoleEnabled = shouldShowDevConsole(showDevConsole);

  // 清理资源
  useEffect(() => {
    return () => {
      if (runtimeClient) {
        runtimeClient.dispose();
      }
    };
  }, [runtimeClient]);

  return (
    <ToastProvider>
      <CopilotContextProvider value={copilotContextValue}>
        <MessagesContextProvider value={messagesContextValue}>
          {children}
          {showDevConsoleEnabled && (
            <div style={{
              position: "fixed",
              bottom: "10px",
              right: "10px",
              background: "rgba(0, 0, 0, 0.8)",
              color: "white",
              padding: "8px",
              borderRadius: "4px",
              fontSize: "12px",
              zIndex: 10000,
            }}>
              CopilotKit Next Dev Console
            </div>
          )}
        </MessagesContextProvider>
      </CopilotContextProvider>
    </ToastProvider>
  );
} 