import * as packageJson from "../../package.json";
import { ErrorHandler } from "./error-handler";
import { Message, convertMessagesToJSON } from "./message-types";

export interface CopilotClientOptions {
  url: string;
  publicApiKey?: string;
  headers?: Record<string, string>;
  credentials?: RequestCredentials;
  properties?: Record<string, any>;
  onError?: (error: Error) => void;
  onWarning?: (warning: string) => void;
}

export interface GenerateResponseRequest {
  messages: Message[];
  actions?: ProcessedAction[];
  context?: string;
  threadId?: string;
  agentSession?: AgentSession;
  extensions?: Extensions;
  forwardedParameters?: ForwardedParameters;
}

export interface ProcessedAction {
  name: string;
  description: string;
  parameters: any[];
  available: "enabled" | "disabled" | "remote";
}

export interface AgentSession {
  agentName: string;
  threadId?: string;
  nodeName?: string;
}

export interface Extensions {
  [key: string]: any;
}

export interface ForwardedParameters {
  temperature?: number;
}

export interface ChatResponse {
  threadId: string;
  runId?: string;
  messages: any[];
  extensions?: Extensions;
  status: ResponseStatus;
}

export interface ResponseStatus {
  code: "success" | "error" | "pending";
  reason?: string;
  details?: string;
}

export interface Agent {
  name: string;
  description?: string;
  configuration?: any;
}

export interface AgentStateRequest {
  agentName: string;
  threadId: string;
}

export interface AgentStateResponse {
  agentName: string;
  threadId: string;
  state: any;
  running: boolean;
  nodeName?: string;
  runId?: string;
  active: boolean;
}

export class CopilotRestClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private abortController?: AbortController;
  private errorHandler: ErrorHandler;

  constructor(options: CopilotClientOptions) {
    this.baseUrl = options.url.replace(/\/$/, ""); // 移除末尾斜杠
    this.errorHandler = new ErrorHandler({
      onError: options.onError,
      onWarning: options.onWarning,
    });

    this.headers = {
      "Content-Type": "application/json",
      "X-CopilotKit-Version": packageJson.version,
      ...options.headers,
    };

    if (options.publicApiKey) {
      this.headers["X-CopilotCloud-Public-API-Key"] = options.publicApiKey;
    }

    // 创建初始的 AbortController
    this.abortController = new AbortController();
  }

  // 发起聊天请求
  async generateResponse(data: GenerateResponseRequest): Promise<ChatResponse> {
    try {
      const requestBody = {
        ...data,
        messages: convertMessagesToJSON(data.messages),
      };

      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify(requestBody),
        signal: this.abortController?.signal,
        credentials: this.getCredentials(),
      });

      await this.errorHandler.handleFetchResponse(response);
      return await response.json();
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 获取可用代理
  async getAvailableAgents(): Promise<Agent[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents`, {
        method: "GET",
        headers: this.headers,
        credentials: this.getCredentials(),
      });

      await this.errorHandler.handleFetchResponse(response);
      return await response.json();
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 加载代理状态
  async loadAgentState(params: AgentStateRequest): Promise<AgentStateResponse> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/agents/${encodeURIComponent(params.agentName)}/state?threadId=${encodeURIComponent(params.threadId)}`,
        {
          method: "GET",
          headers: this.headers,
          credentials: this.getCredentials(),
        }
      );

      await this.errorHandler.handleFetchResponse(response);
      return await response.json();
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 更新代理状态
  async updateAgentState(
    agentName: string,
    threadId: string,
    state: any
  ): Promise<AgentStateResponse> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/agents/${encodeURIComponent(agentName)}/state`,
        {
          method: "POST",
          headers: this.headers,
          body: JSON.stringify({ threadId, state }),
          credentials: this.getCredentials(),
        }
      );

      await this.errorHandler.handleFetchResponse(response);
      return await response.json();
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 启动代理
  async startAgent(agentName: string, config?: any): Promise<void> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/agents/${encodeURIComponent(agentName)}/start`,
        {
          method: "POST",
          headers: this.headers,
          body: JSON.stringify({ config }),
          credentials: this.getCredentials(),
        }
      );

      await this.errorHandler.handleFetchResponse(response);
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 停止代理
  async stopAgent(agentName: string): Promise<void> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/agents/${encodeURIComponent(agentName)}/stop`,
        {
          method: "POST",
          headers: this.headers,
          credentials: this.getCredentials(),
        }
      );

      await this.errorHandler.handleFetchResponse(response);
    } catch (error) {
      this.errorHandler.handleNetworkError(error as Error);
      throw error;
    }
  }

  // 中止当前请求
  abort() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = new AbortController();
    }
  }

  // 获取认证凭据设置
  private getCredentials(): RequestCredentials | undefined {
    // 如果有公共 API 密钥，通常不需要凭据
    if (this.headers["X-CopilotCloud-Public-API-Key"]) {
      return undefined;
    }
    // 否则使用默认的 same-origin
    return "same-origin";
  }

  // 健康检查
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        headers: this.headers,
      });
      return response.ok;
    } catch {
      return false;
    }
  }
} 