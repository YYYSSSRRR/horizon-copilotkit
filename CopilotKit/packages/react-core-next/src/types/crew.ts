/**
 * 需要用户输入的响应或动作状态
 */
export type CrewsResponseStatus = "inProgress" | "complete" | "executing";

/**
 * ResponseRenderer 的响应数据结构
 */
export interface CrewsResponse {
  /**
   * 响应的唯一标识符
   */
  id: string;

  /**
   * 要显示的响应内容
   */
  content: string;

  /**
   * 响应的可选元数据
   */
  metadata?: Record<string, any>;
}

/**
 * 代理状态项的基础接口
 */
export interface CrewsStateItem {
  /**
   * 项目的唯一标识符
   */
  id: string;

  /**
   * 项目创建时间戳
   */
  timestamp: string;
}

/**
 * 工具执行状态项
 */
export interface CrewsToolStateItem extends CrewsStateItem {
  /**
   * 执行的工具名称
   */
  tool: string;

  /**
   * 工具执行的可选思考过程
   */
  thought?: string;

  /**
   * 工具执行的结果
   */
  result?: any;
}

/**
 * 任务状态项
 */
export interface CrewsTaskStateItem extends CrewsStateItem {
  /**
   * 任务名称
   */
  name: string;

  /**
   * 任务描述
   */
  description?: string;
}

/**
 * 包含步骤和任务信息的 AgentState
 */
export interface CrewsAgentState {
  /**
   * 工具执行步骤数组
   */
  steps?: CrewsToolStateItem[];

  /**
   * 任务数组
   */
  tasks?: CrewsTaskStateItem[];
} 