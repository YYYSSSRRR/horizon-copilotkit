import { useState, useEffect } from "react";
import { CopilotSidebar, CopilotKitCSSProperties } from "@copilotkit/react-ui";
import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { MessageSquare, Settings, Activity, Database, Send } from "lucide-react";
import { TextMessage, Role } from "@copilotkit/runtime-client-gql";

export default function HomePage() {
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'loading'>('loading');
  const [backendActions, setBackendActions] = useState<any[]>([]);
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [debugLogs, setDebugLogs] = useState<string[]>([]);

  // 使用 useCopilotChat 来监控消息流
  const {
    isLoading,
    visibleMessages,
    appendMessage,
    stopGeneration,
  } = useCopilotChat();

  // 添加调试日志函数
  const addDebugLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugLogs(prev => [...prev.slice(-9), `[${timestamp}] ${message}`]);
    console.log(`[CopilotKit Debug] ${message}`);
  };

  // 监控消息变化和加载状态
  useEffect(() => {
    addDebugLog(`Messages updated: ${visibleMessages.length} total, isLoading: ${isLoading}`);
    if (visibleMessages.length > 0) {
      const lastMessage = visibleMessages[visibleMessages.length - 1];
      if (lastMessage.isTextMessage()) {
        const textMessage = lastMessage as any; // TextMessage
        addDebugLog(`Last message: role=${textMessage.role}, content length=${textMessage.content?.length || 0}`);
        addDebugLog(`Content preview: "${textMessage.content?.substring(0, 50)}..."`);
      } else {
        addDebugLog(`Last message: type=${lastMessage.constructor.name}, id=${lastMessage.id}`);
      }
    }
    
    // 🔧 检测长时间加载状态
    if (isLoading) {
      const loadingTimeout = setTimeout(() => {
        if (isLoading) {
          addDebugLog("⚠️ 检测到长时间加载状态，可能存在流式响应问题");
          console.warn("CopilotKit: 长时间加载状态，建议检查DeepSeek流式响应");
        }
      }, 15000); // 15秒超时警告

      return () => clearTimeout(loadingTimeout);
    }
  }, [visibleMessages, isLoading]);

  // 测试消息发送函数 - 添加重试机制
  const sendTestMessage = async () => {
    try {
      addDebugLog('Sending test message...');
      // 添加时间戳使每次消息都是唯一的，避免缓存问题
      const timestamp = new Date().toLocaleTimeString();
      const testMessage = new TextMessage({
        content: `现在几点了？请使用getCurrentTime函数获取准确时间 (${timestamp})`,
        role: Role.User,
      });
      
      // 🔧 添加超时检测
      const sendTimeout = setTimeout(() => {
        if (isLoading) {
          addDebugLog('⚠️ 消息发送超时，尝试停止并重试');
          stopGeneration();
        }
      }, 20000); // 20秒超时
      
      await appendMessage(testMessage);
      clearTimeout(sendTimeout);
      addDebugLog('Test message sent successfully');
    } catch (error) {
      addDebugLog(`Failed to send test message: ${error}`);
      console.error('Send message error:', error);
    }
  };

  // 动态获取后端 URL
  const getBackendUrl = () => {
    if (import.meta.env.VITE_BACKEND_URL) {
      return import.meta.env.VITE_BACKEND_URL;
    }
    const currentProtocol = window.location.protocol;
    const currentHostname = window.location.hostname;
    const backendPort = '3001';
    return `${currentProtocol}//${currentHostname}:${backendPort}`;
  };

  const backendUrl = getBackendUrl();

  // 检查后端连接状态
  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await fetch(`${backendUrl}/health`);
        if (response.ok) {
          setBackendStatus('connected');
          const health = await response.json();
          setDebugInfo(health);
          addDebugLog('Backend health check successful');
        } else {
          setBackendStatus('disconnected');
          addDebugLog(`Backend health check failed: ${response.status}`);
        }
      } catch (error) {
        setBackendStatus('disconnected');
        addDebugLog(`Backend connection error: ${error}`);
      }
    };

    const fetchActions = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/actions`);
        if (response.ok) {
          const data = await response.json();
          setBackendActions(data.actions);
          addDebugLog(`Fetched ${data.actions.length} actions`);
        }
      } catch (error) {
        addDebugLog(`Failed to fetch actions: ${error}`);
      }
    };

    checkBackendStatus();
    fetchActions();

    // 每30秒检查一次状态
    const interval = setInterval(checkBackendStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // 注册前端 Action 来测试工具调用
  useCopilotAction({
    name: "showNotification",
    description: "显示前端通知消息",
    parameters: [
      {
        name: "message",
        description: "通知消息内容",
        type: "string",
        required: true,
      },
      {
        name: "type",
        description: "通知类型: success, error, warning, info",
        type: "string",
        required: false,
      },
    ],
    handler: ({ message, type = "info" }: { message: string; type?: string }) => {
      addDebugLog(`Frontend action called: showNotification(${message}, ${type})`);
      alert(`${type.toUpperCase()}: ${message}`);
      return `已显示通知: ${message}`;
    },
  });

  return (
    <div 
      className="flex h-screen bg-gradient-to-br from-blue-50 to-indigo-100"
      style={{
        "--copilot-kit-primary-color": "#3b82f6",
      } as CopilotKitCSSProperties}
    >
      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white shadow-sm border-b p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MessageSquare className="text-blue-600" size={24} />
              <h1 className="text-xl font-semibold text-gray-800">
                CopilotKit Debug Example (DeepSeek + Vite)
              </h1>
              <span className={`status-indicator ${backendStatus}`}></span>
              <span className="text-sm text-gray-600">
                后端状态: {backendStatus === 'connected' ? '已连接' : backendStatus === 'disconnected' ? '断开连接' : '连接中...'}
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                消息数: {visibleMessages.length} | 加载中: {isLoading ? '是' : '否'} | Actions: {backendActions.length}
              </span>
              <button
                onClick={sendTestMessage}
                disabled={backendStatus !== 'connected' || isLoading}
                className="flex items-center space-x-2 px-3 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
              >
                <Send size={14} />
                <span>{isLoading ? '发送中...' : '测试消息'}</span>
              </button>
              {isLoading && (
                <button
                  onClick={stopGeneration}
                  className="flex items-center space-x-2 px-3 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 text-sm"
                >
                  <span>停止生成</span>
                </button>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center">
                <Settings className="mr-2" size={20} />
                实时调试信息
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 后端状态 */}
                <div className="debug-panel p-4">
                  <h3 className="flex items-center">
                    <Activity className="mr-2" size={16} />
                    后端健康状态
                  </h3>
                  {debugInfo ? (
                    <pre className="text-xs">{JSON.stringify(debugInfo, null, 2)}</pre>
                  ) : (
                    <p className="text-gray-500">获取中...</p>
                  )}
                </div>

                {/* 可用 Actions */}
                <div className="debug-panel p-4">
                  <h3 className="flex items-center">
                    <Database className="mr-2" size={16} />
                    可用 Actions
                  </h3>
                  {backendActions.length > 0 ? (
                    <div className="space-y-2">
                      {backendActions.map((action: any, index: number) => (
                        <div key={index} className="border rounded p-2 bg-gray-50">
                          <div className="font-medium text-sm">{action.name}</div>
                          <div className="text-xs text-gray-600">{action.description}</div>
                          <div className="text-xs text-gray-500">
                            参数: {action.parameters?.length || 0}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">暂无可用 Actions</p>
                  )}
                </div>

                {/* 调试日志 */}
                <div className="debug-panel p-4">
                  <h3 className="flex items-center">
                    <MessageSquare className="mr-2" size={16} />
                    调试日志
                  </h3>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {debugLogs.length > 0 ? (
                      debugLogs.map((log, index) => (
                        <div key={index} className="text-xs font-mono bg-gray-100 p-1 rounded">
                          {log}
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-xs">等待调试日志...</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 消息详情 */}
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">💬 消息详情</h2>
              <div className="space-y-2">
                {visibleMessages.length > 0 ? (
                  visibleMessages.map((message, index) => (
                    <div key={index} className="border rounded p-3 bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-medium text-sm">
                            消息 #{index + 1} - ID: {message.id}
                          </div>
                          <div className="text-xs text-gray-600">
                            类型: {message.constructor.name}
                          </div>
                          {message.isTextMessage() && (
                            <div className="mt-2">
                              <div className="text-xs text-gray-500">
                                角色: {(message as any).role}
                              </div>
                              <div className="text-sm bg-white p-2 rounded mt-1 border">
                                {(message as any).content || '(无内容)'}
                              </div>
                            </div>
                          )}
                          {message.isActionExecutionMessage && message.isActionExecutionMessage() && (
                            <div className="mt-2">
                              <div className="text-xs text-gray-500">
                                Action 名称: {(message as any).actionName}
                              </div>
                              <div className="text-xs text-gray-500">
                                执行 ID: {(message as any).id}
                              </div>
                              <div className="text-sm bg-blue-50 p-2 rounded mt-1 border border-blue-200">
                                🔧 正在执行 Action...
                              </div>
                            </div>
                          )}
                          {message.isResultMessage && message.isResultMessage() && (
                            <div className="mt-2">
                              <div className="text-xs text-gray-500">
                                Action 名称: {(message as any).actionName}
                              </div>
                              <div className="text-xs text-gray-500">
                                Action ID: {(message as any).actionExecutionId}
                              </div>
                              <div className="text-sm bg-green-50 p-2 rounded mt-1 border border-green-200">
                                <div className="font-medium text-green-700 mb-1">✅ 执行结果:</div>
                                <div className="text-green-800">{(message as any).result || '(无结果)'}</div>
                              </div>
                            </div>
                          )}
                          {!message.isTextMessage() && 
                           !(message.isActionExecutionMessage && message.isActionExecutionMessage()) && 
                           !(message.isResultMessage && message.isResultMessage()) && (
                            <div className="mt-2">
                              <div className="text-sm bg-gray-100 p-2 rounded mt-1 border">
                                <div className="text-xs text-gray-500 mb-1">消息详情:</div>
                                <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                                  {JSON.stringify(message, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500">暂无消息</p>
                )}
              </div>
            </div>

            {/* 使用说明 */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-lg font-semibold mb-4">🔍 调试说明</h2>
              <div className="space-y-4 text-sm text-gray-600">
                <div>
                  <h3 className="font-medium text-gray-800 mb-2">实时监控:</h3>
                  <ul className="list-disc list-inside space-y-1">
                    <li>消息数量: <strong>{visibleMessages.length}</strong></li>
                    <li>当前状态: <strong>{isLoading ? '加载中' : '空闲'}</strong></li>
                    <li>后端连接: <strong>{backendStatus}</strong></li>
                    <li>可用 Actions: <strong>{backendActions.length}</strong></li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium text-gray-800 mb-2">测试 Actions:</h3>
                  <ul className="list-disc list-inside space-y-1">
                    <li>点击右上角的"测试消息"按钮发送测试消息</li>
                    <li>询问当前时间: "现在几点了？"</li>
                    <li>数学计算: "帮我计算 2 + 3 * 4"</li>
                    <li>查询用户: "查询用户ID为1的信息"</li>
                    <li>运行时状态: "获取运行时调试状态"</li>
                    <li>前端通知: "显示一个成功通知"</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium text-gray-800 mb-2">调试提示:</h3>
                  <ul className="list-disc list-inside space-y-1">
                    <li>查看右侧调试日志面板</li>
                    <li>注意消息数量和加载状态变化</li>
                    <li>如果卡在加载中，检查后端流式响应</li>
                    <li>使用浏览器开发者工具查看网络请求</li>
                    <li>查看上方的"消息详情"面板了解具体消息内容</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* CopilotKit 聊天界面 */}
      <CopilotSidebar
        labels={{
          title: "AI 助手 (DeepSeek + Vite 调试模式)",
          initial: "👋 你好！我是 CopilotKit + DeepSeek + Vite 调试助手。\n\n🔧 **调试功能:**\n- 使用 DeepSeek Chat 模型\n- 基于 Vite 构建，启动更快\n- 可以执行多种自定义 Actions\n- 后端使用 Express + CopilotKit Runtime + DeepSeek Adapter\n- 你可以在代码中设置断点进行调试\n\n💡 **试试问我:**\n- \"现在几点了？\"\n- \"计算 10 + 20 * 3\"\n- \"查询用户1的信息\"\n- \"获取运行时状态\"\n- \"显示一个通知\"\n\n⚡ **调试提示:**\n- 查看左侧调试面板的日志\n- 如果第一次没有回复，请稍等或重试\n- 每次问题都会添加时间戳避免缓存\n\n让我们开始调试吧！",
          placeholder: "输入消息进行调试...",
        }}
        defaultOpen={true}
        clickOutsideToClose={false}
        className="w-96 border-l"
        instructions="你是一个专业的调试助手。当用户询问时间、计算、用户信息或运行时状态时，请务必使用对应的 Action 函数来获取准确信息。不要猜测答案，而是调用相应的函数。"
      />
    </div>
  );
} 