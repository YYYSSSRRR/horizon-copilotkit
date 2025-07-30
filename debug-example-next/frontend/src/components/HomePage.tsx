import { useState, useEffect, useMemo, useCallback } from 'react'
import { 
  useCopilotChat, 
  useCopilotAction,
  useCopilotScriptAction, 
  useCopilotReadable,
  useToast,
  TextMessage 
} from '@copilotkit/react-core-next'
import { askLlmAction, fillFormAction } from '../../playwright-scripts/index.js'


export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<string>('检查中...')
  const [currentTime, setCurrentTime] = useState<string>('')
  const [calculation, setCalculation] = useState<string>('')
  const [userInfo, setUserInfo] = useState<string>('')
  const [systemStatus, setSystemStatus] = useState<string>('')
  
  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    age: '',
    gender: '',
    country: '',
    skills: [] as string[],
    bio: '',
    newsletter: false,
    priority: 'medium',
    startDate: '',
    endDate: ''
  })

  const { toast } = useToast()
  
  // 表单处理函数
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    toast(`表单已提交！姓名: ${formData.name}`, 'success')
    console.log('表单数据:', formData)
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSkillToggle = (skill: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.includes(skill)
        ? prev.skills.filter(s => s !== skill)
        : [...prev.skills, skill]
    }))
  }

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      age: '',
      gender: '',
      country: '',
      skills: [],
      bio: '',
      newsletter: false,
      priority: 'medium',
      startDate: '',
      endDate: ''
    })
    toast('表单已重置', 'info')
  }
  
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
  const notificationAction = useMemo(() => ({
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
  }), []);

  useCopilotAction(notificationAction);

  useCopilotScriptAction(askLlmAction);
  useCopilotScriptAction(fillFormAction);

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
    <div className="min-h-screen bg-gray-50 p-2 sm:p-4">
      {/* 头部 */}
      <header className="max-w-7xl mx-auto mb-8">
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

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6">
        {/* 表单区域 */}
        <div className="lg:col-span-4">
          <UserInfoForm 
            formData={formData}
            onInputChange={handleInputChange}
            onSkillToggle={handleSkillToggle}
            onSubmit={handleFormSubmit}
            onReset={resetForm}
          />
        </div>

        {/* 聊天区域 */}
        <div className="lg:col-span-5">
          <div className="bg-white rounded-lg shadow-lg h-[600px] flex flex-col">
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
        <div className="lg:col-span-3 space-y-4">
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

// 用户信息表单组件
function UserInfoForm({ 
  formData, 
  onInputChange, 
  onSkillToggle, 
  onSubmit, 
  onReset 
}: {
  formData: any,
  onInputChange: (field: string, value: any) => void,
  onSkillToggle: (skill: string) => void,
  onSubmit: (e: React.FormEvent) => void,
  onReset: () => void
}) {
  const skillOptions = ['React', 'TypeScript', 'Node.js', 'Python', 'Java', 'Go'];
  const countryOptions = ['中国', '美国', '日本', '德国', '法国', '英国'];

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6 h-fit">
      <h2 className="text-lg font-semibold mb-4">📝 用户信息表单</h2>
      <p className="text-sm text-gray-600 mb-4">
        这个表单用于测试 ScriptAction 的界面操作功能
      </p>
      
      <form onSubmit={onSubmit} className="space-y-4">
        {/* 姓名和邮箱 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              姓名 *
            </label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={(e) => onInputChange('name', e.target.value)}
              placeholder="请输入您的姓名"
              aria-label="姓名输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              邮箱 *
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={(e) => onInputChange('email', e.target.value)}
              placeholder="请输入您的邮箱"
              aria-label="邮箱输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
        </div>

        {/* 年龄和国家 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-1">
              年龄
            </label>
            <input
              id="age"
              name="age"
              type="number"
              min="1"
              max="150"
              value={formData.age}
              onChange={(e) => onInputChange('age', e.target.value)}
              placeholder="请输入您的年龄"
              aria-label="年龄输入框"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-1">
              国家
            </label>
            <select
              id="country"
              name="country"
              value={formData.country}
              onChange={(e) => onInputChange('country', e.target.value)}
              aria-label="国家选择"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">请选择国家</option>
              {countryOptions.map(country => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 性别和优先级 - 并排布局 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">性别</label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="male"
                  checked={formData.gender === 'male'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="男性"
                  className="mr-2"
                />
                男
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="female"
                  checked={formData.gender === 'female'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="女性"
                  className="mr-2"
                />
                女
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="gender"
                  value="other"
                  checked={formData.gender === 'other'}
                  onChange={(e) => onInputChange('gender', e.target.value)}
                  aria-label="其他"
                  className="mr-2"
                />
                其他
              </label>
            </div>
          </div>
          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              优先级
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={(e) => onInputChange('priority', e.target.value)}
              aria-label="优先级选择"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </div>
        </div>


        {/* 技能多选框 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">技能</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {skillOptions.map(skill => (
              <label key={skill} className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.skills.includes(skill)}
                  onChange={() => onSkillToggle(skill)}
                  aria-label={`技能: ${skill}`}
                  className="mr-2"
                />
                {skill}
              </label>
            ))}
          </div>
        </div>


        {/* 日期范围 */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
              开始日期
            </label>
            <input
              id="startDate"
              name="startDate"
              type="date"
              value={formData.startDate}
              onChange={(e) => onInputChange('startDate', e.target.value)}
              aria-label="开始日期"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
              结束日期
            </label>
            <input
              id="endDate"
              name="endDate"
              type="date"
              value={formData.endDate}
              onChange={(e) => onInputChange('endDate', e.target.value)}
              aria-label="结束日期"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* 个人简介文本区域 */}
        <div>
          <label htmlFor="bio" className="block text-sm font-medium text-gray-700 mb-1">
            个人简介
          </label>
          <textarea
            id="bio"
            name="bio"
            rows={3}
            value={formData.bio}
            onChange={(e) => onInputChange('bio', e.target.value)}
            placeholder="请简单介绍一下自己..."
            aria-label="个人简介"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* 通讯录订阅复选框 */}
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.newsletter}
              onChange={(e) => onInputChange('newsletter', e.target.checked)}
              aria-label="订阅通讯录"
              className="mr-2"
            />
            订阅通讯录
          </label>
        </div>

        {/* 按钮组 */}
        <div className="flex space-x-2 pt-4">
          <button
            type="submit"
            aria-label="提交表单"
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            提交
          </button>
          <button
            type="button"
            onClick={onReset}
            aria-label="重置表单"
            className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            重置
          </button>
        </div>
      </form>

      {/* 表单数据预览 */}
      <div className="mt-6 p-4 bg-gray-50 rounded-md">
        <h3 className="text-sm font-medium text-gray-700 mb-2">当前表单数据:</h3>
        <pre className="text-xs text-gray-600 overflow-auto max-h-32">
          {JSON.stringify(formData, null, 2)}
        </pre>
      </div>
    </div>
  )
} 