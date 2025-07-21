import { CopilotRestClient } from "./rest-client";
import { StreamProcessor } from "./stream-processor";
import { 
  CopilotClientOptions, 
  GenerateResponseRequest, 
  ChatResponse, 
  Agent, 
  AgentStateRequest, 
  AgentStateResponse 
} from "./rest-client";
import { Message } from "./message-types";

export interface StreamResponseOptions {
  onMessage?: (message: Message) => void;
  onComplete?: (messages: Message[]) => void;
  onError?: (error: Error) => void;
}

export class CopilotRuntimeClient {
  private restClient: CopilotRestClient;
  private streamProcessor: StreamProcessor;

  constructor(options: CopilotClientOptions) {
    this.restClient = new CopilotRestClient(options);
    this.streamProcessor = new StreamProcessor();
  }

  // 统一的响应生成接口，使用 SSE 流式传输
  async generateResponse(
    data: GenerateResponseRequest, 
    stream = false,
    options: StreamResponseOptions = {}
  ): Promise<ChatResponse | Message[]> {
    if (stream) {
      return this.generateSSEStreamResponse(data, options);
    } else {
      return this.restClient.generateResponse(data);
    }
  }

  // SSE 流式响应（使用 Server-Sent Events）
  private async generateSSEStreamResponse(
    data: GenerateResponseRequest,
    options: StreamResponseOptions
  ): Promise<Message[]> {
    try {
      const requestBody = {
        ...data,
        messages: data.messages.map(m => m.toJSON()),
        stream: true, // 启用流式响应
      };

      const response = await fetch(`${this.restClient['baseUrl']}/api/chat/stream`, {
        method: "POST",
        headers: {
          ...this.restClient['headers'],
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(requestBody),
        signal: this.restClient['abortController']?.signal,
      });

      await this.restClient['errorHandler'].handleFetchResponse(response);

      // 设置流处理器回调
      this.streamProcessor = new StreamProcessor({
        onMessage: options.onMessage,
        onComplete: options.onComplete,
        onError: options.onError,
      });

      // 根据响应类型处理流
      const contentType = response.headers.get('Content-Type') || '';
      
      if (contentType.includes('text/event-stream')) {
        // Server-Sent Events
        return await this.streamProcessor.processSSEStream(response);
      } else {
        // 分块传输编码
        return await this.streamProcessor.processChunkedResponse(response);
      }
    } catch (error) {
      if (options.onError) {
        options.onError(error as Error);
      }
      throw error;
    }
  }

  // 获取可用代理
  async getAvailableAgents(): Promise<Agent[]> {
    return this.restClient.getAvailableAgents();
  }

  // 加载代理状态
  async loadAgentState(params: AgentStateRequest): Promise<AgentStateResponse> {
    return this.restClient.loadAgentState(params);
  }

  // 更新代理状态
  async updateAgentState(
    agentName: string,
    threadId: string,
    state: any
  ): Promise<AgentStateResponse> {
    return this.restClient.updateAgentState(agentName, threadId, state);
  }

  // 启动代理
  async startAgent(agentName: string, config?: any): Promise<void> {
    return this.restClient.startAgent(agentName, config);
  }

  // 停止代理
  async stopAgent(agentName: string): Promise<void> {
    return this.restClient.stopAgent(agentName);
  }

  // 中止所有请求
  abort() {
    this.restClient.abort();
  }

  // 健康检查
  async healthCheck(): Promise<boolean> {
    return this.restClient.healthCheck();
  }

  // 创建流式转换器（用于高级用例）
  createMessageTransformStream(): TransformStream<Uint8Array, Message> {
    return this.streamProcessor.createTransformStream();
  }

  // 获取客户端统计信息
  getClientStats() {
    return {
      lastMessages: this.streamProcessor.getMessages(),
    };
  }

  // 获取基础URL
  getBaseUrl(): string {
    return (this.restClient as any).baseUrl;
  }

  // 清理资源
  dispose(): void {
    this.abort();
    this.streamProcessor.clear();
  }
}

// 便捷工厂函数
export function createCopilotRuntimeClient(options: CopilotClientOptions): CopilotRuntimeClient {
  return new CopilotRuntimeClient(options);
} 