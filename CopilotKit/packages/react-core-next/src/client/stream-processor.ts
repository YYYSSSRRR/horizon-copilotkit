import { Message, TextMessage, convertJSONToMessages } from "./message-types";

export interface StreamProcessorOptions {
  onMessage?: (message: Message) => void;
  onComplete?: (messages: Message[]) => void;
  onError?: (error: Error) => void;
}

export class StreamProcessor {
  private messages: Message[] = [];
  private options: StreamProcessorOptions;

  constructor(options: StreamProcessorOptions = {}) {
    this.options = options;
  }

  // 处理 ReadableStream
  async processStream(stream: ReadableStream<Message>): Promise<Message[]> {
    const reader = stream.getReader();
    this.messages = [];

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        if (value) {
          this.messages.push(value);
          
          // 调用消息回调
          if (this.options.onMessage) {
            this.options.onMessage(value);
          }
        }
      }

      // 调用完成回调
      if (this.options.onComplete) {
        this.options.onComplete(this.messages);
      }

      return this.messages;
    } catch (error) {
      // 调用错误回调
      if (this.options.onError) {
        this.options.onError(error as Error);
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  }

  // 处理 Server-Sent Events (SSE) 流
  async processSSEStream(
    response: Response,
    parseMessage: (data: string) => Message | null = (data: string) => this.parseSSEMessage(data)
  ): Promise<Message[]> {
    if (!response.body) {
      throw new Error("Response body is null");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    this.messages = [];

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        // 解码数据块
        buffer += decoder.decode(value, { stream: true });
        
        // 处理完整的行
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // 保留不完整的行

        for (const line of lines) {
          if (line.trim()) {
            try {
              const message = parseMessage(line.trim());
              if (message) {
                this.messages.push(message);
                
                if (this.options.onMessage) {
                  this.options.onMessage(message);
                }
              }
            } catch (error) {
              console.warn("Failed to parse SSE message:", line, error);
            }
          }
        }
      }

      // 处理剩余的缓冲区
      if (buffer.trim()) {
        try {
          const message = parseMessage(buffer.trim());
          if (message) {
            this.messages.push(message);
            
            if (this.options.onMessage) {
              this.options.onMessage(message);
            }
          }
        } catch (error) {
          console.warn("Failed to parse final SSE message:", buffer, error);
        }
      }

      if (this.options.onComplete) {
        this.options.onComplete(this.messages);
      }

      return this.messages;
    } catch (error) {
      if (this.options.onError) {
        this.options.onError(error as Error);
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  }

  // 默认的 SSE 消息解析器
  private parseSSEMessage(data: string): Message | null {
    // 处理 SSE 格式: "data: {...}"
    if (data.startsWith("data: ")) {
      const jsonStr = data.substring(6);
      
      if (jsonStr === "[DONE]") {
        return null; // 流结束标记
      }

      try {
        const parsed = JSON.parse(jsonStr);
        
        // 检查是否是流式事件而不是完整消息
        if (this.isStreamEvent(parsed)) {
          // 处理流式事件：通过回调传递，但不添加到消息数组
          const pseudoMessage = this.createPseudoMessageFromStreamEvent(parsed);
          if (pseudoMessage && this.options.onMessage) {
            this.options.onMessage(pseudoMessage);
          }
          // 返回 null，不添加到消息数组
          return null;
        } else {
          // 处理完整消息
          if (parsed.type) {
            const messages = convertJSONToMessages([parsed]);
            return messages[0] || null;
          } else {
            // 处理没有type字段的元数据，不是消息
            return null;
          }
        }
      } catch (error) {
        console.warn("Failed to parse SSE JSON:", jsonStr, error);
        return null;
      }
    }

    return null;
  }

  // 检查是否是流式事件
  private isStreamEvent(data: any): boolean {
    const streamEventTypes = [
      "session_start",
      "session_end", 
      "message_start",
      "text_content", // 新增：支持累加内容事件
      "text_end", // 文本消息结束
      "message_end",
      "action_execution_start",
      "action_execution_args", 
      "action_execution_end",
      "action_execution_result",
      "error",
      "ping",
      "heartbeat"
    ];
    
    return streamEventTypes.includes(data.type);
  }

  // 将流式事件转换为伪消息，用于回调处理
  private createPseudoMessageFromStreamEvent(eventData: any): Message | null {
    const { type, data, timestamp } = eventData;
    
    // 创建一个伪文本消息来承载事件数据，用于回调处理
    // 注意：这不是一个真正的消息，只是为了传递事件数据，不会被添加到最终消息数组
    const pseudoMessage = new TextMessage({
      content: "",
      role: "assistant",
    });
    
    // 对于 action_execution_args，数据在顶层而不是嵌套在 data 中
    if (type === "action_execution_args") {
      (pseudoMessage as any).eventType = type;
      (pseudoMessage as any).eventData = eventData; // 使用整个 eventData 对象
      (pseudoMessage as any).timestamp = timestamp;
    } else {
      // 添加事件特定的属性
      (pseudoMessage as any).eventType = type;
      (pseudoMessage as any).eventData = data;
      (pseudoMessage as any).timestamp = timestamp;
    }
    
    return pseudoMessage;
  }

  // 处理分块传输编码的响应
  async processChunkedResponse(
    response: Response,
    parseChunk: (chunk: string) => Message[] = this.parseJSONChunk
  ): Promise<Message[]> {
    if (!response.body) {
      throw new Error("Response body is null");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    this.messages = [];

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        
        try {
          const chunkMessages = parseChunk(chunk);
          
          for (const message of chunkMessages) {
            this.messages.push(message);
            
            if (this.options.onMessage) {
              this.options.onMessage(message);
            }
          }
        } catch (error) {
          console.warn("Failed to parse chunk:", chunk, error);
        }
      }

      if (this.options.onComplete) {
        this.options.onComplete(this.messages);
      }

      return this.messages;
    } catch (error) {
      if (this.options.onError) {
        this.options.onError(error as Error);
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  }

  // 默认的 JSON 块解析器
  private parseJSONChunk(chunk: string): Message[] {
    try {
      // 尝试解析为单个 JSON 对象
      const parsed = JSON.parse(chunk);
      
      if (Array.isArray(parsed)) {
        return convertJSONToMessages(parsed);
      } else {
        return convertJSONToMessages([parsed]);
      }
    } catch (error) {
      // 如果不是完整的 JSON，尝试按行分割解析
      const lines = chunk.split("\n").filter(line => line.trim());
      const messages: Message[] = [];
      
      for (const line of lines) {
        try {
          const parsed = JSON.parse(line);
          const lineMessages = convertJSONToMessages(Array.isArray(parsed) ? parsed : [parsed]);
          messages.push(...lineMessages);
        } catch (lineError) {
          // 忽略无法解析的行
        }
      }
      
      return messages;
    }
  }

  // 获取当前收集的消息
  getMessages(): Message[] {
    return [...this.messages];
  }

  // 清空消息缓存
  clear(): void {
    this.messages = [];
  }

  // 创建转换流，用于 Transform Stream API
  createTransformStream(): TransformStream<Uint8Array, Message> {
    const decoder = new TextDecoder();
    let buffer = "";

    return new TransformStream({
      transform: (chunk, controller) => {
        try {
          buffer += decoder.decode(chunk, { stream: true });
          
          // 尝试解析完整的 JSON 对象
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.trim()) {
              try {
                const parsed = JSON.parse(line.trim());
                const messages = convertJSONToMessages([parsed]);
                messages.forEach(message => controller.enqueue(message));
              } catch (error) {
                // 忽略解析错误
              }
            }
          }
        } catch (error) {
          controller.error(error);
        }
      },
      flush: (controller) => {
        // 处理剩余的缓冲区
        if (buffer.trim()) {
          try {
            const parsed = JSON.parse(buffer.trim());
            const messages = convertJSONToMessages([parsed]);
            messages.forEach(message => controller.enqueue(message));
          } catch (error) {
            // 忽略最终的解析错误
          }
        }
      }
    });
  }
} 