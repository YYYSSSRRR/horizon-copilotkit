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
 * 支持自定义的中断处理逻辑，而不局限于审批流程
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
    if (!partialId) {
      // 如果没有提供 ID，返回最新的未解决中断
      const pending = Array.from(this.pendingInterrupts.values()).filter(req => !req.resolved);
      return pending.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
    }

    // 精确匹配
    if (this.pendingInterrupts.has(partialId)) {
      return this.pendingInterrupts.get(partialId);
    }

    // 部分匹配
    for (const [id, request] of this.pendingInterrupts) {
      if (id.includes(partialId) || partialId.includes(id)) {
        return request;
      }
    }

    return undefined;
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
   * 获取所有待处理中断
   */
  getPendingInterrupts(): InterruptRequest[] {
    return Array.from(this.pendingInterrupts.values()).filter(req => !req.resolved);
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

  // ================================
  // 向后兼容方法（用于旧的审批API）
  // ================================

  /**
   * 向后兼容：请求审批（映射到中断请求）
   */
  requestApproval(actionName: string, parameters: any): InterruptRequest {
    const { request } = this.createInterrupt(actionName, parameters);
    return request;
  }

  /**
   * 向后兼容：生成审批消息
   */
  generateApprovalMessage(request: InterruptRequest): string {
    return `🔐 **动作审批请求**

动作名称: ${request.actionName}
参数: ${JSON.stringify(request.parameters, null, 2)}
审批ID: ${request.interruptId.slice(-8)}
时间: ${new Date(request.timestamp).toLocaleString()}

请回复 'y' 或 '同意' 批准此操作，或 'n' 或 '拒绝' 取消操作。

⚠️ **重要**: 当你批准或拒绝时，请使用审批ID "${request.interruptId.slice(-8)}" 来确保正确处理。`;
  }

  /**
   * 向后兼容：添加需要审批的动作
   */
  addApprovalRequiredAction(actionName: string): void {
    this.interruptRequiredActions.add(actionName);
  }

  /**
   * 向后兼容：移除需要审批的动作
   */
  removeApprovalRequiredAction(actionName: string): void {
    this.interruptRequiredActions.delete(actionName);
  }

  /**
   * 向后兼容：通过部分ID查找审批请求
   */
  findApprovalByPartialId(partialId: string): InterruptRequest | undefined {
    return this.findInterruptByPartialId(partialId);
  }

  /**
   * 向后兼容：获取待审批列表
   */
  getPendingApprovals(): InterruptRequest[] {
    return this.getPendingInterrupts();
  }

}