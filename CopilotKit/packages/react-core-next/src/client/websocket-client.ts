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
    // 将 HTTP URL 转换为 WebSocket URL
    this.url = options.url
      .replace(/^http/, "ws")
      .replace(/\/$/, "") + "/ws";
    
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

  // 连接 WebSocket
  async connect(): Promise<void> {
    if (this.isConnected || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        // 构建包含认证信息的 URL
        const wsUrl = new URL(this.url);
        
        // 将 headers 作为查询参数添加
        Object.entries(this.headers).forEach(([key, value]) => {
          wsUrl.searchParams.set(key, value);
        });

        this.ws = new WebSocket(wsUrl.toString());

        this.ws.onopen = () => {
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
          this.isConnecting = false;
          this.errorHandler.handleWebSocketError(event);
          reject(new Error("WebSocket connection failed"));
        };

        this.ws.onclose = (event) => {
          this.isConnected = false;
          this.isConnecting = false;
          
          // 如果不是正常关闭，尝试重连
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

      } catch (error) {
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