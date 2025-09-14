import { randomId } from "@copilotkit/shared";

// 中断请求接口
export interface InterruptRequest {
  interruptId: string;
  sessionId: string;
  actionName: string;
  parameters: any;
  timestamp: string;
  resolved: boolean;
  resumeData?: any; // 用户交互返回的数据
}

// 中断处理器接口
export interface InterruptHandler {
  /**
   * 当动作被中断时调用，返回用于显示给用户的中断消息/UI数据
   * 支持异步操作，可以调用AI生成选项等
   */
  onInterrupt: (actionName: string, parameters: any, interruptId: string) => any | Promise<any>;
  
  /**
   * 当用户提供恢复数据时调用，返回最终的动作执行结果
   */
  onResume: (actionName: string, originalParameters: any, resumeData: any) => Promise<any>;
}

/**
 * 通用前端中断管理器
 * 支持自定义的中断处理逻辑
 */
export class FrontendInterruptManager {
  private pendingInterrupts = new Map<string, InterruptRequest>();
  private interruptRequiredActions = new Set<string>();
  private interruptHandlers = new Map<string, InterruptHandler>();
  private sessionId = randomId();

  /**
   * 注册需要中断的动作及其处理器
   */
  registerInterruptAction(actionName: string, handler: InterruptHandler): void {
    this.interruptRequiredActions.add(actionName);
    this.interruptHandlers.set(actionName, handler);
  }

  /**
   * 取消注册中断动作
   */
  unregisterInterruptAction(actionName: string): void {
    this.interruptRequiredActions.delete(actionName);
    this.interruptHandlers.delete(actionName);
  }

  /**
   * 检查动作是否需要中断
   */
  requiresInterrupt(actionName: string): boolean {
    return this.interruptRequiredActions.has(actionName);
  }

  /**
   * 获取动作的中断处理器
   */
  getInterruptHandler(actionName: string): InterruptHandler | undefined {
    return this.interruptHandlers.get(actionName);
  }

  /**
   * 创建中断请求
   * @param actionName 动作名称
   * @param parameters 动作参数
   * @returns 中断请求和显示数据
   */
  createInterrupt(actionName: string, parameters: any): { request: InterruptRequest; displayData: any } {
    const interruptId = `interrupt-${randomId()}`;
    const request: InterruptRequest = {
      interruptId,
      sessionId: this.sessionId,
      actionName,
      parameters,
      timestamp: new Date().toISOString(),
      resolved: false
    };

    this.pendingInterrupts.set(interruptId, request);
    console.log(`[中断管理器] 创建中断请求: ${interruptId}, 动作: ${actionName}, 当前待处理数量: ${this.getPendingInterrupts().length}`);

    // 获取中断处理器并生成显示数据
    const handler = this.interruptHandlers.get(actionName);
    let displayData = `动作 "${actionName}" 需要用户交互，请处理中断ID: ${interruptId}`;
    
    if (handler) {
      try {
        displayData = handler.onInterrupt(actionName, parameters, interruptId);
      } catch (error) {
        console.error(`中断处理器错误:`, error);
        displayData = `中断处理器执行失败: ${error}`;
      }
    }

    return { request, displayData };
  }

  /**
   * 创建异步中断请求（支持AI生成等异步操作）
   * @param actionName 动作名称
   * @param parameters 动作参数
   * @returns Promise包含中断请求和显示数据
   */
  async createInterruptAsync(actionName: string, parameters: any): Promise<{ request: InterruptRequest; displayData: any }> {
    const interruptId = `interrupt-${randomId()}`;
    const request: InterruptRequest = {
      interruptId,
      sessionId: this.sessionId,
      actionName,
      parameters,
      timestamp: new Date().toISOString(),
      resolved: false
    };

    this.pendingInterrupts.set(interruptId, request);

    // 获取中断处理器并生成显示数据
    const handler = this.interruptHandlers.get(actionName);
    let displayData = `动作 "${actionName}" 需要用户交互，请处理中断ID: ${interruptId}`;
    
    if (handler) {
      try {
        const result = handler.onInterrupt(actionName, parameters, interruptId);
        // 支持异步处理
        displayData = await Promise.resolve(result);
      } catch (error) {
        console.error(`中断处理器错误:`, error);
        displayData = `中断处理器执行失败: ${error}`;
      }
    }

    return { request, displayData };
  }

  /**
   * 根据部分 ID 查找中断请求
   */
  findInterruptByPartialId(partialId: string): InterruptRequest | undefined {
    console.log(`[中断管理器] 查找中断请求: partialId="${partialId}", 总中断数: ${this.pendingInterrupts.size}`);
    
    const allInterrupts = Array.from(this.pendingInterrupts.values());
    const pendingInterrupts = allInterrupts.filter(req => !req.resolved);
    
    console.log(`[中断管理器] 当前待处理中断: ${pendingInterrupts.length}个`);
    pendingInterrupts.forEach(req => {
      console.log(`  - ${req.interruptId} (${req.actionName}) - ${req.timestamp}`);
    });

    if (!partialId) {
      // 如果没有提供 ID，返回最新的未解决中断
      const latest = pendingInterrupts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
      console.log(`[中断管理器] 返回最新中断: ${latest?.interruptId || '无'}`);
      return latest;
    }

    // 精确匹配
    if (this.pendingInterrupts.has(partialId)) {
      const request = this.pendingInterrupts.get(partialId)!;
      console.log(`[中断管理器] 精确匹配找到: ${request.interruptId}`);
      return request;
    }

    // 部分匹配
    for (const [id, request] of this.pendingInterrupts) {
      if (id.includes(partialId) || partialId.includes(id)) {
        console.log(`[中断管理器] 部分匹配找到: ${request.interruptId}`);
        return request;
      }
    }

    console.log(`[中断管理器] 未找到匹配的中断请求`);
    return undefined;
  }

  /**
   * 获取待处理的中断请求列表
   */
  getPendingInterrupts(): InterruptRequest[] {
    return Array.from(this.pendingInterrupts.values()).filter(req => !req.resolved);
  }

  /**
   * 恢复中断的动作执行
   * @param interruptId 中断ID（可以是部分ID）
   * @param resumeData 用户提供的恢复数据
   * @returns 动作执行结果
   */
  async resumeAction(interruptId: string, resumeData: any): Promise<any> {
    const request = this.findInterruptByPartialId(interruptId);
    
    if (!request) {
      const pendingCount = Array.from(this.pendingInterrupts.values()).filter(r => !r.resolved).length;
      throw new Error(
        pendingCount > 0
          ? `找不到匹配的中断请求。当前有 ${pendingCount} 个待处理的中断。`
          : '没有找到待处理的中断请求。'
      );
    }

    if (request.resolved) {
      throw new Error(`中断请求 ${request.interruptId.slice(-8)} 已经被处理过了。`);
    }

    // 标记为已解决
    request.resolved = true;
    request.resumeData = resumeData;

    // 获取中断处理器并执行恢复逻辑
    const handler = this.interruptHandlers.get(request.actionName);
    if (!handler) {
      throw new Error(`动作 "${request.actionName}" 没有注册中断处理器`);
    }

    try {
      const result = await handler.onResume(request.actionName, request.parameters, resumeData);
      return result;
    } catch (error) {
      console.error(`恢复动作执行失败:`, error);
      throw new Error(`恢复动作执行失败: ${error}`);
    }
  }


  /**
   * 取消中断请求
   */
  cancelInterrupt(interruptId: string): boolean {
    const request = this.findInterruptByPartialId(interruptId);
    if (request && !request.resolved) {
      request.resolved = true;
      return true;
    }
    return false;
  }

  /**
   * 清理已解决的中断请求（保留最近的一些记录）
   */
  cleanup(keepRecentCount: number = 10): void {
    const resolved = Array.from(this.pendingInterrupts.entries())
      .filter(([_, req]) => req.resolved)
      .sort((a, b) => new Date(b[1].timestamp).getTime() - new Date(a[1].timestamp).getTime());

    // 保留最近的记录，删除其余的
    resolved.slice(keepRecentCount).forEach(([id, _]) => {
      this.pendingInterrupts.delete(id);
    });
  }

  /**
   * 获取中断统计信息
   */
  getStats(): {
    totalInterrupts: number;
    pendingCount: number;
    resolvedCount: number;
    actionStats: Record<string, number>;
  } {
    const allInterrupts = Array.from(this.pendingInterrupts.values());
    const pending = allInterrupts.filter(req => !req.resolved);
    const resolved = allInterrupts.filter(req => req.resolved);
    
    const actionStats: Record<string, number> = {};
    allInterrupts.forEach(req => {
      actionStats[req.actionName] = (actionStats[req.actionName] || 0) + 1;
    });

    return {
      totalInterrupts: allInterrupts.length,
      pendingCount: pending.length,
      resolvedCount: resolved.length,
      actionStats
    };
  }

}