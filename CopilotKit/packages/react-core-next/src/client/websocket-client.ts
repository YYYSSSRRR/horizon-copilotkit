import { randomId } from "@copilotkit/shared";
import { ErrorHandler } from "./error-handler";
import { CopilotClientOptions, GenerateResponseRequest } from "./rest-client";
import { convertJSONToMessages, Message } from "./message-types";

export interface WebSocketMessage {
  id: string;
  type: string;
  data?: any;
  error?: string;
}

export interface StreamChunk {
  type: "message_chunk" | "stream_end" | "error" | "meta_event";
  data?: any;
  error?: string;
}

export class CopilotWebSocketClient {
  private ws?: WebSocket;
  private url: string;
  private headers: Record<string, string>;
  private messageQueue: any[] = [];
  private isConnected = false;
  private isConnecting = false;
  private errorHandler: ErrorHandler;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000;

  constructor(options: CopilotClientOptions) {
    // 构建 WebSocket URL，支持相对和绝对路径
    this.url = this.buildWebSocketUrl(options.url);
    
    this.headers = options.headers || {};
    this.errorHandler = new ErrorHandler({
      onError: options.onError,
      onWarning: options.onWarning,
    });

    // 添加公共 API 密钥到连接参数
    if (options.publicApiKey) {
      this.headers["X-CopilotCloud-Public-API-Key"] = options.publicApiKey;
    }
  }

  // 构建 WebSocket URL
  private buildWebSocketUrl(url: string): string {
    try {
      // 如果是相对路径，构建完整的 URL
      if (url.startsWith('/')) {
        if (typeof window !== 'undefined') {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          return `${protocol}//${host}${url.replace(/\/$/, "")}/ws`;
        } else {
          // 服务器端或无法获取 window 对象时，返回相对 WebSocket URL
          return `ws://localhost:3000${url.replace(/\/$/, "")}/ws`;
        }
      }

      // 处理绝对路径
      const httpUrl = new URL(url);
      
      // 将协议转换为 WebSocket
      const wsProtocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // 构建 WebSocket URL
      return `${wsProtocol}//${httpUrl.host}${httpUrl.pathname.replace(/\/$/, "")}/ws${httpUrl.search}`;
      
    } catch (error) {
      this.errorHandler?.handleError(new Error(`Failed to build WebSocket URL from "${url}": ${error}`));
      // 回退到默认 URL
      if (typeof window !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/api/copilotkit/ws`;
      }
      return 'ws://localhost:3000/api/copilotkit/ws';
    }
  }

  // 连接 WebSocket
  async connect(): Promise<void> {
    if (this.isConnected || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        // 验证 WebSocket URL
        if (!this.url) {
          throw new Error("WebSocket URL is not defined");
        }

        let wsUrl: URL;
        try {
          wsUrl = new URL(this.url);
        } catch (error) {
          throw new Error(`Invalid WebSocket URL "${this.url}": ${error}`);
        }

        // 验证 WebSocket 协议
        if (!wsUrl.protocol.startsWith('ws')) {
          throw new Error(`Invalid WebSocket protocol "${wsUrl.protocol}". Expected "ws:" or "wss:"`);
        }
        
        // 将 headers 作为查询参数添加
        Object.entries(this.headers).forEach(([key, value]) => {
          if (value) {
            wsUrl.searchParams.set(key, value);
          }
        });

        console.log(`🔌 Attempting WebSocket connection to: ${wsUrl.toString()}`);

        this.ws = new WebSocket(wsUrl.toString());

        this.ws.onopen = () => {
          console.log(`✅ WebSocket connected to: ${wsUrl.toString()}`);
          this.isConnected = true;
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          
          // 发送队列中的消息
          this.flushMessageQueue();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            this.errorHandler.handleError(new Error(`Failed to parse WebSocket message: ${error}`));
          }
        };

        this.ws.onerror = (event) => {
          console.error(`❌ WebSocket error:`, event);
          this.isConnecting = false;
          this.errorHandler.handleWebSocketError(event);
          reject(new Error(`WebSocket connection failed to ${wsUrl.toString()}`));
        };

        this.ws.onclose = (event) => {
          console.log(`🔌 WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
          this.isConnected = false;
          this.isConnecting = false;
          
          // 如果不是正常关闭，尝试重连
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

      } catch (error) {
        console.error(`❌ WebSocket connection setup failed:`, error);
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  // 发送消息并接收流式响应
  streamResponse(data: GenerateResponseRequest): ReadableStream<Message> {
    return new ReadableStream({
      start: (controller) => {
        const messageId = randomId();
        
        // 注册消息处理器
        this.messageHandlers.set(messageId, (response: StreamChunk) => {
          try {
            if (response.type === "message_chunk" && response.data) {
              // 解析消息数据
              const messages = convertJSONToMessages([response.data]);
              messages.forEach(message => controller.enqueue(message));
            } else if (response.type === "stream_end") {
              controller.close();
              this.messageHandlers.delete(messageId);
            } else if (response.type === "error") {
              controller.error(new Error(response.error || "Stream error"));
              this.messageHandlers.delete(messageId);
            }
          } catch (error) {
            controller.error(error);
            this.messageHandlers.delete(messageId);
          }
        });

        // 发送请求
        this.send({
          id: messageId,
          type: "generate_response",
          data: {
            ...data,
            messages: data.messages.map(m => m.toJSON()),
          },
        });
      },
      cancel: () => {
        // 清理资源
        this.messageHandlers.clear();
      }
    });
  }

  // 发送单个消息
  private send(data: WebSocketMessage) {
    if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      // 如果未连接，将消息加入队列
      this.messageQueue.push(data);
      
      // 尝试连接
      if (!this.isConnected && !this.isConnecting) {
        this.connect().catch(error => {
          this.errorHandler.handleError(error);
        });
      }
    }
  }

  // 处理接收到的消息
  private handleMessage(message: WebSocketMessage) {
    const handler = this.messageHandlers.get(message.id);
    if (handler) {
      handler(message.data);
    } else {
      // 处理其他类型的消息（如系统消息、心跳等）
      if (message.type === "ping") {
        this.send({ id: randomId(), type: "pong" });
      }
    }
  }

  // 刷新消息队列
  private flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.isConnected && this.ws) {
      const message = this.messageQueue.shift();
      this.ws.send(JSON.stringify(message));
    }
  }

  // 尝试重连
  private attemptReconnect() {
    this.reconnectAttempts++;
    
    setTimeout(() => {
      this.errorHandler.handleWarning(
        `Attempting to reconnect WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
      );
      
      this.connect().catch(error => {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.errorHandler.handleError(
            new Error(`Failed to reconnect after ${this.maxReconnectAttempts} attempts`)
          );
        }
      });
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  // 断开连接
  disconnect() {
    this.messageHandlers.clear();
    this.messageQueue = [];
    
    if (this.ws) {
      this.ws.close(1000, "Client disconnected");
      this.ws = undefined;
    }
    
    this.isConnected = false;
    this.isConnecting = false;
  }

  // 检查连接状态
  isReady(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  // 等待连接就绪
  async waitForConnection(timeout = 5000): Promise<void> {
    if (this.isReady()) {
      return;
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error("WebSocket connection timeout"));
      }, timeout);

      const checkConnection = () => {
        if (this.isReady()) {
          clearTimeout(timeoutId);
          resolve();
        } else if (!this.isConnecting) {
          clearTimeout(timeoutId);
          reject(new Error("WebSocket connection failed"));
        } else {
          setTimeout(checkConnection, 100);
        }
      };

      checkConnection();
    });
  }
} 