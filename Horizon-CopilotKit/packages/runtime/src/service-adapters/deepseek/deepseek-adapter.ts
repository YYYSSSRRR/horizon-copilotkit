/**
 * Copilot Runtime adapter for DeepSeek.
 *
 * ## Example
 *
 * ```ts
 * import { CopilotRuntime, DeepSeekAdapter } from "@copilotkit/runtime";
 * import OpenAI from "openai";
 *
 * const copilotKit = new CopilotRuntime();
 *
 * const deepseek = new OpenAI({
 *   apiKey: "<your-deepseek-api-key>",
 *   baseURL: "https://api.deepseek.com/v1",
 * });
 *
 * return new DeepSeekAdapter({ openai: deepseek });
 * ```
 *
 * ## Available Models
 *
 * DeepSeek supports the following models:
 * - deepseek-chat (default): DeepSeek's flagship model optimized for chat
 * - deepseek-coder: Specialized for code generation and understanding
 * - deepseek-reasoner: Enhanced reasoning capabilities
 */
import OpenAI from "openai";
import {
  CopilotServiceAdapter,
  CopilotRuntimeChatCompletionRequest,
  CopilotRuntimeChatCompletionResponse,
} from "../service-adapter";
import {
  convertActionInputToOpenAITool,
  convertMessageToOpenAIMessage,
  limitMessagesToTokenCount,
} from "../openai/utils";
import { randomUUID } from "@copilotkit/shared";

const DEFAULT_MODEL = "deepseek-chat";
const DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1";

export interface DeepSeekAdapterParams {
  /**
   * An OpenAI-compatible instance configured for DeepSeek.
   * If not provided, a new instance will be created with DeepSeek's base URL.
   */
  openai?: OpenAI;

  /**
   * DeepSeek API key. Required if openai instance is not provided.
   */
  apiKey?: string;

  /**
   * The DeepSeek model to use.
   * Available models: deepseek-chat, deepseek-coder, deepseek-reasoner
   *
   * @default "deepseek-chat"
   */
  model?: string;

  /**
   * Whether to disable parallel tool calls.
   * DeepSeek supports parallel tool calls for efficiency.
   *
   * @default false
   */
  disableParallelToolCalls?: boolean;

  /**
   * Custom base URL for DeepSeek API.
   * 
   * @default "https://api.deepseek.com/v1"
   */
  baseURL?: string;

  /**
   * Additional headers to send with requests.
   */
  headers?: Record<string, string>;
}

export class DeepSeekAdapter implements CopilotServiceAdapter {
  private model: string = DEFAULT_MODEL;
  private disableParallelToolCalls: boolean = false;
  private _openai: OpenAI;

  public get openai(): OpenAI {
    return this._openai;
  }

  constructor(params?: DeepSeekAdapterParams) {
    if (params?.openai) {
      this._openai = params.openai;
    } else {
      if (!params?.apiKey) {
        throw new Error("DeepSeek API key is required when openai instance is not provided");
      }
      
      this._openai = new OpenAI({
        apiKey: params.apiKey,
        baseURL: params?.baseURL || DEEPSEEK_BASE_URL,
        defaultHeaders: {
          "User-Agent": "CopilotKit-DeepSeek-Adapter",
          ...params?.headers,
        },
      });
    }

    if (params?.model) {
      this.model = params.model;
    }
    this.disableParallelToolCalls = params?.disableParallelToolCalls || false;
  }

  async process(
    request: CopilotRuntimeChatCompletionRequest,
  ): Promise<CopilotRuntimeChatCompletionResponse> {
    const {
      threadId: threadIdFromRequest,
      model = this.model,
      messages,
      actions,
      eventSource,
      forwardedParameters,
    } = request;
    console.log("🔄 [DeepSeek] Processing request:", {
      threadId: threadIdFromRequest,
      model,
      messagesCount: messages.length,
      actionsCount: actions.length,
      timestamp: new Date().toISOString()
    });
    const tools = actions.map(convertActionInputToOpenAITool);
    const threadId = threadIdFromRequest ?? randomUUID();

    // ALLOWLIST APPROACH: Only include tool_result messages that correspond to valid tool_calls
    // Step 1: Extract valid tool_call IDs
    const validToolUseIds = new Set<string>();

    for (const message of messages) {
      if (message.isActionExecutionMessage()) {
        validToolUseIds.add(message.id);
      }
    }

    // Step 2: Filter messages, keeping only those with valid tool_call IDs
    const filteredMessages = messages.filter((message) => {
      if (message.isResultMessage()) {
        // Skip if there's no corresponding tool_call
        if (!validToolUseIds.has(message.actionExecutionId)) {
          return false;
        }

        // Remove this ID from valid IDs so we don't process duplicates
        validToolUseIds.delete(message.actionExecutionId);
        return true;
      }

      // Keep all non-tool-result messages
      return true;
    });

    let openaiMessages = filteredMessages.map((m) =>
      convertMessageToOpenAIMessage(m, { 
        // DeepSeek prefers 'system' role for system messages
        keepSystemRole: true 
      }),
    );
    
    // 🔧 DeepSeek 兼容性修复：将不支持的 'developer' 角色转换为 'system'
    openaiMessages = openaiMessages.map((message) => {
      if (message && typeof message === 'object' && 'role' in message && message.role === 'developer') {
        console.log('🔄 [DeepSeek] Converting developer role to system role');
        return {
          ...message,
          role: 'system' as const,
        };
      }
      return message;
    });
    
    openaiMessages = limitMessagesToTokenCount(openaiMessages, tools, model);

    let toolChoice: any = forwardedParameters?.toolChoice;
    if (forwardedParameters?.toolChoice === "function") {
      toolChoice = {
        type: "function",
        function: { name: forwardedParameters.toolChoiceFunctionName },
      };
    }

    console.log("📤 [DeepSeek] Sending request to API:", {
      model,
      messagesCount: openaiMessages.length,
      toolsCount: tools.length,
      messages: openaiMessages.map(m => ({ role: m.role, content: typeof m.content === 'string' ? m.content.substring(0, 100) + '...' : typeof m.content }))
    });

    try {
      const requestPayload = {
        model: model,
        stream: true as const,
        messages: openaiMessages,
        ...(tools.length > 0 && { tools }),
        ...(forwardedParameters?.maxTokens && { max_tokens: forwardedParameters.maxTokens }),
        ...(forwardedParameters?.stop && { stop: forwardedParameters.stop }),
        ...(toolChoice && { tool_choice: toolChoice }),
        ...(this.disableParallelToolCalls && { parallel_tool_calls: false }),
        ...(forwardedParameters?.temperature && { 
          temperature: Math.max(0.1, Math.min(2.0, forwardedParameters.temperature)) // DeepSeek temperature range
        }),
      };

      console.log("📤 [DeepSeek] API Request payload:", JSON.stringify(requestPayload, null, 2));

      const stream = this.openai.beta.chat.completions.stream(requestPayload);

      console.log("🔄 [DeepSeek] Stream created successfully, starting to process...");
      console.log("🔄 [DeepSeek] Stream object:", typeof stream, stream.constructor.name);

      eventSource.stream(async (eventStream$) => {
        let mode: "function" | "message" | null = null;
        let currentMessageId: string = "";
        let currentToolCallId: string = "";
        let currentActionName: string = ""; // 跟踪当前执行的 Action 名称

        try {
          console.log("🔄 [DeepSeek] Starting stream iteration...");
          let chunkCount = 0;
          let lastChunkTime = Date.now();
          
          for await (const chunk of stream) {
            lastChunkTime = Date.now();
            chunkCount++;
            
            console.log(`📦 [DeepSeek] Received chunk #${chunkCount}:`, { 
              choicesLength: chunk.choices.length,
              finishReason: chunk.choices[0]?.finish_reason,
              hasToolCall: !!chunk.choices[0]?.delta.tool_calls?.[0],
              hasContent: !!chunk.choices[0]?.delta.content,
            });

            if (chunk.choices.length === 0) {
              continue;
            }

            const toolCall = chunk.choices[0].delta.tool_calls?.[0];
            const content = chunk.choices[0].delta.content;
            const finishReason = chunk.choices[0].finish_reason;

            // 🔧 检查是否应该结束流
            if (finishReason) {
              console.log(`🏁 [DeepSeek] Finish reason detected: ${finishReason}, will end after processing this chunk`);
            }

            // 🔧 关键修复：使用 OpenAI 适配器的模式切换逻辑
            // When switching from message to function or vice versa, send the respective end event.
            if (mode === "message" && toolCall?.id) {
              console.log("🔧 [DeepSeek] Switching from message to function mode");
              mode = null;
              eventStream$.sendTextMessageEnd({ messageId: currentMessageId });
            } else if (mode === "function" && (toolCall === undefined || toolCall?.id)) {
              console.log("🔧 [DeepSeek] Switching from function to message mode");
              mode = null;
              eventStream$.sendActionExecutionEnd({ actionExecutionId: currentToolCallId });
            }

            // If we send a new message type, send the appropriate start event.
            if (mode === null) {
              if (toolCall?.id) {
                console.log("🚀 [DeepSeek] Starting function mode");
                mode = "function";
                currentToolCallId = toolCall.id;
                currentActionName = toolCall.function?.name || "";
                eventStream$.sendActionExecutionStart({
                  actionExecutionId: currentToolCallId,
                  parentMessageId: chunk.id,
                  actionName: currentActionName,
                });
              } else if (content) {
                console.log("💬 [DeepSeek] Starting message mode");
                mode = "message";
                currentMessageId = chunk.id || randomUUID();
                eventStream$.sendTextMessageStart({ messageId: currentMessageId });
              }
            }

            // send the content events
            if (mode === "message" && content) {
              console.log("💬 [DeepSeek] Sending text content:", content);
              eventStream$.sendTextMessageContent({
                messageId: currentMessageId,
                content: content,
              });
            } else if (mode === "function" && toolCall?.function?.arguments) {
              console.log("📝 [DeepSeek] Sending function arguments:", toolCall.function.arguments);
              eventStream$.sendActionExecutionArgs({
                actionExecutionId: currentToolCallId,
                args: toolCall.function.arguments,
              });
            }

            // 🔧 强制在 finishReason 后结束流
            if (finishReason) {
              console.log(`🔚 [DeepSeek] Breaking loop due to finish reason: ${finishReason}`);
              break;
            }
          }

          // 🔧 关键修复：确保流正确结束 - 来自 OpenAI 适配器  
          console.log(`🏁 [DeepSeek] Stream loop ended after ${chunkCount} chunks, sending final events`);
          
          // send the end events
          if (mode === "message") {
            console.log("💬 [DeepSeek] Ending final text message");
            eventStream$.sendTextMessageEnd({ messageId: currentMessageId });
          } else if (mode === "function") {
            console.log("🔧 [DeepSeek] Ending final function execution");
            eventStream$.sendActionExecutionEnd({ actionExecutionId: currentToolCallId });
          }
        } catch (error) {
          console.error("❌ [DeepSeek] streaming error:", error);
          if (mode === "message") {
            console.log("💬 [DeepSeek] Error cleanup: ending text message");
            eventStream$.sendTextMessageEnd({
              messageId: currentMessageId,
            });
          } else if (mode === "function" && currentToolCallId) {
            console.log("🔧 [DeepSeek] Error cleanup: ending function execution");
            eventStream$.sendActionExecutionEnd({
              actionExecutionId: currentToolCallId,
            });
          }
          throw error;
        }

        // 🔧 关键修复：明确完成事件流 - 来自 OpenAI 适配器
        console.log("🎉 [DeepSeek] Completing event stream");
        eventStream$.complete();
      });

      return { threadId };
    } catch (error) {
      console.error("DeepSeek API error:", error);
      throw new Error(`DeepSeek API request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
} 