import { useState, useEffect, useMemo, useCallback } from 'react'
import { 
  useCopilotChat, 
  useCopilotAction, 
  useCopilotReadable,
  useToast,
  TextMessage 
} from '@copilotkit/react-core-next'

export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<string>('检查中...')
  const [currentTime, setCurrentTime] = useState<string>('')
  const [calculation, setCalculation] = useState<string>('')
  const [userInfo, setUserInfo] = useState<string>('')
  const [systemStatus, setSystemStatus] = useState<string>('')

  const { toast } = useToast()
  
  // 检查后端状态
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch('/health')
        if (response.ok) {
          const data = await response.json()
          setBackendStatus(`✅ 后端正常运行 (${data.adapter?.provider}: ${data.adapter?.model})`)
        } else {
          setBackendStatus('❌ 后端连接失败')
        }
      } catch (error) {
        setBackendStatus('❌ 后端不可用')
      }
    }
    checkBackend()
  }, [])

  // 缓存动作处理器
  const timeHandler = useCallback(async (args: any) => {
    const { timezone } = args || {}
    const result = `当前时间: ${new Date().toLocaleString('zh-CN', { 
      timeZone: timezone || 'Asia/Shanghai' 
    })}`
    setCurrentTime(result)
    toast('时间查询成功！', 'success')
    return result
  }, [setCurrentTime, toast])

  // 定义Copilot动作 - 时间查询
  const timeAction = useMemo(() => ({
    name: "get_current_time",
    description: "获取当前时间",
    parameters: [
      {
        name: "timezone",
        type: "string",
        description: "时区 (默认: Asia/Shanghai)",
        required: false
      }
    ],
    handler: timeHandler
  }), [timeHandler])

  // useCopilotAction(timeAction)

  const calculateHandler = useCallback(async (args: any) => {
    const { expression } = args || {}
    try {
      // 简单的安全计算（仅支持基本运算）
      const allowedChars = /^[0-9+\-*/(). ]+$/
      if (!allowedChars.test(expression)) {
        throw new Error('表达式包含不支持的字符')
      }
      
      const result = eval(expression)
      const resultText = `计算结果: ${expression} = ${result}`
      setCalculation(resultText)
      toast('计算完成！', 'success')
      return resultText
    } catch (error) {
      const errorText = `计算错误: ${error instanceof Error ? error.message : '未知错误'}`
      setCalculation(errorText)
      toast('计算失败！', 'error')
      return errorText
    }
  }, [setCalculation, toast])

  // 定义Copilot动作 - 数学计算
  const calculateAction = useMemo(() => ({
    name: "calculate",
    description: "执行数学计算",
    parameters: [
      {
        name: "expression",
        type: "string", 
        description: "数学表达式 (如: 2+3*4)",
        required: true
      }
    ],
    handler: calculateHandler
  }), [calculateHandler])

  // useCopilotAction(calculateAction)

  const userInfoHandler = useCallback(async (args: any) => {
    const { type } = args || {}
    let result = ''
    if (type === 'system') {
      result = `系统信息:\n- 浏览器: ${navigator.userAgent}\n- 平台: ${navigator.platform}\n- 语言: ${navigator.language}`
    } else {
      result = '用户: 调试用户\n状态: 在线\n权限: 标准用户'
    }
    setUserInfo(result)
    toast('信息获取成功！', 'info')
    return result
  }, [setUserInfo, toast])

  // 定义Copilot动作 - 用户信息
  const userInfoAction = useMemo(() => ({
    name: "get_user_info",
    description: "获取用户或系统信息",
    parameters: [
      {
        name: "type",
        type: "string",
        description: "信息类型: basic(基本信息) 或 system(系统信息)",
        required: false
      }
    ],
    handler: userInfoHandler
  }), [userInfoHandler])

  // useCopilotAction(userInfoAction)

  const statusHandler = useCallback(async (args: any) => {
    const { component } = args || {}
    const status = {
      frontend: "✅ React 前端运行中",
      backend: backendStatus,
      copilotkit: "✅ CopilotKit 已连接",
      actions: "✅ 4 个动作可用"
    }
    
    let result = ''
    if (component === 'all' || !component) {
      result = Object.entries(status).map(([k, v]) => `${k}: ${v}`).join('\n')
    } else if (component in status) {
      result = `${component}: ${status[component as keyof typeof status]}`
    } else {
      result = `未知组件: ${component}。可用组件: ${Object.keys(status).join(', ')}`
    }
    
    setSystemStatus(result)
    toast('状态检查完成！', 'info')
    return result
  }, [backendStatus, setSystemStatus, toast])

  // 定义Copilot动作 - 状态检查
  const statusAction = useMemo(() => ({
    name: "check_status", 
    description: "检查系统状态",
    parameters: [
      {
        name: "component",
        type: "string",
        description: "要检查的组件 (frontend, backend, all)",
        required: false
      }
    ],
    handler: statusHandler
  }), [statusHandler])

  // useCopilotAction(statusAction)

  // 注册前端 Action 来测试工具调用
  useCopilotAction(useCallback({
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
      alert(`${type.toUpperCase()}: ${message}`);
      return `已显示通知: ${message}`;
    },
  }, []));

  // 使用CopilotChat
  const { 
    visibleMessages, 
    appendMessage, 
    setMessages, 
    reloadMessages,
    stopGeneration,
    isLoading 
  } = useCopilotChat()

  // 让Copilot了解当前页面内容 - 使用 useMemo 避免无限循环
  const readableDescription = useMemo(() => "调试页面信息和状态", []);
  const readableValue = useMemo(() => `
    这是一个CopilotKit调试示例页面。
    当前状态:
    - 后端状态: ${backendStatus}
    - 最新时间查询: ${currentTime}
    - 最新计算结果: ${calculation}
    - 用户信息: ${userInfo}
    - 系统状态: ${systemStatus}
    
    可用功能:
    1. 获取当前时间 (get_current_time)
    2. 数学计算 (calculate)
    3. 查询用户信息 (get_user_info) 
    4. 检查系统状态 (check_status)
  `, [backendStatus, currentTime, calculation, userInfo, systemStatus])

  useCopilotReadable({
    description: readableDescription,
    value: readableValue,
    dependencies: [readableDescription, readableValue]
  })

  const handleSendMessage = (message: string) => {
    if (message.trim()) {
      appendMessage(new TextMessage({ content: message, role: 'user' }))
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* 头部 */}
      <header className="max-w-4xl mx-auto mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🚀 CopilotKit Debug Example Next
        </h1>
        <p className="text-gray-600">
          基于 react-core-next 和 runtime-next 的调试示例
        </p>
        <div className="mt-4 p-3 bg-white rounded-lg shadow">
          <span className="text-sm font-medium text-gray-700">后端状态: </span>
          <span className="text-sm">{backendStatus}</span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 聊天区域 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-lg h-96 flex flex-col">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold">💬 AI 助手聊天</h2>
              <p className="text-sm text-gray-600">
                尝试说: "现在几点了？" 或 "计算 2+3*4" 或 "检查系统状态"
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {visibleMessages.map((message, index) => {
                // 只显示文本消息
                if (!message.isTextMessage()) {
                  return null;
                }

                console.log(message.status.code, message.content);
                
                const textMessage = message;
                return (
                  <div
                    key={index}
                    className={`flex ${
                      textMessage.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        textMessage.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-800'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{textMessage.content}</p>
                    </div>
                  </div>
                );
              })}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 px-4 py-2 rounded-lg">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-100"></div>
                      <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t">
              <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
              {isLoading && (
                <button
                  onClick={stopGeneration}
                  className="mt-2 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                >
                  停止生成
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 侧边栏 - 状态信息 */}
        <div className="space-y-4">
          {/* 快速操作 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">🎮 快速操作</h3>
            <div className="space-y-2">
              <button
                onClick={() => handleSendMessage("现在几点了？")}
                className="w-full px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                获取时间
              </button>
              <button
                onClick={() => handleSendMessage("计算 15*8+24")}
                className="w-full px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600"
              >
                数学计算
              </button>
              <button
                onClick={() => handleSendMessage("查看我的用户信息")}
                className="w-full px-3 py-2 text-sm bg-purple-500 text-white rounded hover:bg-purple-600"
              >
                用户信息
              </button>
                <button
                  onClick={() => handleSendMessage("检查系统状态")}
                  className="w-full px-3 py-2 text-sm bg-orange-500 text-white rounded hover:bg-orange-600"
                >
                  系统状态
                </button>
                <button
                  onClick={() => handleSendMessage("显示通知消息")}
                  className="w-full px-3 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                >
                  显示通知
                </button>
            </div>
          </div>

          {/* 实时状态 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">📊 实时状态</h3>
            <div className="space-y-3 text-sm">
              {currentTime && (
                <div>
                  <span className="font-medium text-blue-600">⏰ 时间:</span>
                  <p className="text-gray-700 mt-1">{currentTime}</p>
                </div>
              )}
              
              {calculation && (
                <div>
                  <span className="font-medium text-green-600">🧮 计算:</span>
                  <p className="text-gray-700 mt-1">{calculation}</p>
                </div>
              )}
              
              {userInfo && (
                <div>
                  <span className="font-medium text-purple-600">👤 用户:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{userInfo}</p>
                </div>
              )}
              
              {systemStatus && (
                <div>
                  <span className="font-medium text-orange-600">🔧 状态:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{systemStatus}</p>
                </div>
              )}
            </div>
          </div>

          {/* 消息控制 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">🔧 消息控制</h3>
            <div className="space-y-2">
              <button
                onClick={() => setMessages([])}
                className="w-full px-3 py-2 text-sm bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                清空对话
              </button>
              <button
                onClick={() => reloadMessages('')}
                className="w-full px-3 py-2 text-sm bg-indigo-500 text-white rounded hover:bg-indigo-600"
              >
                重新加载
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// 聊天输入组件
function ChatInput({ onSendMessage, disabled }: { onSendMessage: (message: string) => void, disabled: boolean }) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message)
      setMessage('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex space-x-2">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="输入消息..."
        disabled={disabled}
        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        发送
      </button>
    </form>
  )
} 