import React, { createContext, useContext, ReactNode } from "react";
import { CopilotRuntimeClient } from "../client";
import { FrontendAction } from "../types/frontend-action";
import { CopilotChatSuggestionConfiguration } from "../types/chat-suggestion-configuration";
import { DocumentPointer } from "../types/document-pointer";
import { CoAgentStateRender } from "../types/coagent-action";
import { SystemMessageFunction } from "../types/system-message";
import { LangGraphInterruptAction } from "../hooks/use-langgraph-interrupt";

export interface CopilotReadable {
  categories?: string[];
  description: string;
  value: any;
  convert?: (value: any) => string;
}

export interface CopilotContextValue {
  // 核心客户端
  runtimeClient?: CopilotRuntimeClient;
  
  // 动作系统
  actions: FrontendAction[];
  setAction: (id: string, actionDef: FrontendAction) => void;
  removeAction: (id: string) => void;
  
  // 可读上下文
  readables: Record<string, CopilotReadable>;
  setReadable: (id: string, readable: CopilotReadable) => void;
  removeReadable: (id: string) => void;
  
  // 聊天建议
  chatSuggestions: CopilotChatSuggestionConfiguration[];
  setChatSuggestion: (id: string, suggestion: CopilotChatSuggestionConfiguration) => void;
  removeChatSuggestion: (id: string) => void;
  
  // 文档指针
  documentPointers: DocumentPointer[];
  setDocumentPointer: (id: string, pointer: DocumentPointer) => void;
  removeDocumentPointer: (id: string) => void;
  
  // CoAgent 状态渲染器
  coAgentStateRenders: Record<string, CoAgentStateRender>;
  setCoAgentStateRender: (id: string, render: CoAgentStateRender) => void;
  removeCoAgentStateRender: (id: string) => void;
  
  // 系统消息
  systemMessage?: SystemMessageFunction;
  setSystemMessage: (systemMessage: SystemMessageFunction) => void;
  
  // 聊天指令
  chatInstructions?: string;
  
  // 转发参数
  forwardedParameters?: {
    temperature?: number;
    [key: string]: any;
  };
  
  // 状态管理
  isLoading?: boolean;
  setIsLoading?: (loading: boolean) => void;
  
  // 线程管理
  threadId?: string;
  setThreadId?: (threadId: string) => void;
  runId?: string | null;
  setRunId?: (runId: string | null) => void;
  
  // LangGraph 中断
  langGraphInterruptAction?: LangGraphInterruptAction;
  setLangGraphInterruptAction: (action: Partial<LangGraphInterruptAction>) => void;
  removeLangGraphInterruptAction: (actionId: string) => void;
  
  // 代理会话
  agentSession?: any;
  setAgentSession?: (session: any) => void;
  
  // 认证相关（云服务）
  authConfig_c?: {
    SignInComponent: React.ComponentType<{
      onSignInComplete: (authState: any) => void;
    }>;
  };
  authStates_c?: Record<string, any>;
  setAuthStates_c?: (states: Record<string, any> | ((prev: Record<string, any>) => Record<string, any>)) => void;
  
  // 配置选项
  cloud?: {
    guardrails?: Record<string, any>;
  };
  
  // 辅助方法
  getContextString: (categories?: string[], defaultCategories?: string[]) => string;
  getCoAgentStateRender: (agentName: string, nodeName?: string) => CoAgentStateRender | undefined;
}

const CopilotContext = createContext<CopilotContextValue | undefined>(undefined);

export interface CopilotContextProviderProps {
  children: ReactNode;
  value: CopilotContextValue;
}

export function CopilotContextProvider({ children, value }: CopilotContextProviderProps) {
  return (
    <CopilotContext.Provider value={value}>
      {children}
    </CopilotContext.Provider>
  );
}

export function useCopilotContext(): CopilotContextValue {
  const context = useContext(CopilotContext);
  if (!context) {
    throw new Error("useCopilotContext must be used within a CopilotKit provider");
  }
  return context;
}

// 便捷 Hook
export function useCopilotRuntimeClient() {
  const { runtimeClient } = useCopilotContext();
  if (!runtimeClient) {
    throw new Error("No runtime client found in CopilotKit context");
  }
  return runtimeClient;
}

export function useCopilotActions() {
  const { actions, setAction, removeAction } = useCopilotContext();
  return {
    actions,
    setAction,
    removeAction,
  };
}

export function useCopilotReadables() {
  const { readables, setReadable, removeReadable, getContextString } = useCopilotContext();
  return {
    readables,
    setReadable,
    removeReadable,
    getContextString,
  };
}

export function useCopilotChatSuggestions() {
  const { chatSuggestions, setChatSuggestion, removeChatSuggestion } = useCopilotContext();
  return {
    chatSuggestions,
    setChatSuggestion,
    removeChatSuggestion,
  };
}

export function useCopilotDocumentPointers() {
  const { documentPointers, setDocumentPointer, removeDocumentPointer } = useCopilotContext();
  return {
    documentPointers,
    setDocumentPointer,
    removeDocumentPointer,
  };
}

export function useCopilotCoAgentStateRenders() {
  const { coAgentStateRenders, setCoAgentStateRender, removeCoAgentStateRender, getCoAgentStateRender } = useCopilotContext();
  return {
    coAgentStateRenders,
    setCoAgentStateRender,
    removeCoAgentStateRender,
    getCoAgentStateRender,
  };
} 