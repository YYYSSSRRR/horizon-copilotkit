import { randomId } from "@copilotkit/shared";

// 审批请求接口
export interface FrontendApprovalRequest {
  approvalId: string;
  sessionId: string;
  actionName: string;
  parameters: any;
  timestamp: string;
  resolved: boolean;
}

// 审批决定类型
export type ApprovalDecision = 'approved' | 'rejected';

/**
 * 前端对话式审批管理器
 * 用于管理需要用户审批的前端动作
 */
export class FrontendApprovalManager {
  private pendingApprovals = new Map<string, FrontendApprovalRequest>();
  private approvalRequiredActions = new Set<string>();
  private sessionId = randomId();

  /**
   * 设置需要审批的动作名称列表
   */
  setApprovalRequiredActions(actionNames: string[]): void {
    this.approvalRequiredActions.clear();
    actionNames.forEach(name => this.approvalRequiredActions.add(name));
  }

  /**
   * 添加需要审批的动作
   */
  addApprovalRequiredAction(actionName: string): void {
    this.approvalRequiredActions.add(actionName);
  }

  /**
   * 移除需要审批的动作
   */
  removeApprovalRequiredAction(actionName: string): void {
    this.approvalRequiredActions.delete(actionName);
  }

  /**
   * 检查动作是否需要审批
   */
  requiresApproval(actionName: string): boolean {
    return this.approvalRequiredActions.has(actionName);
  }

  /**
   * 请求审批
   * @param actionName 动作名称
   * @param parameters 动作参数
   * @returns 审批请求信息
   */
  requestApproval(actionName: string, parameters: any): FrontendApprovalRequest {
    const approvalId = `frontend-${randomId()}`;
    const request: FrontendApprovalRequest = {
      approvalId,
      sessionId: this.sessionId,
      actionName,
      parameters,
      timestamp: new Date().toISOString(),
      resolved: false
    };

    this.pendingApprovals.set(approvalId, request);
    return request;
  }

  /**
   * 根据部分 ID 查找审批请求
   */
  findApprovalByPartialId(partialId: string): FrontendApprovalRequest | undefined {
    if (!partialId) {
      // 如果没有提供 ID，返回最新的未解决审批
      const pending = Array.from(this.pendingApprovals.values()).filter(req => !req.resolved);
      return pending.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
    }

    // 精确匹配
    if (this.pendingApprovals.has(partialId)) {
      return this.pendingApprovals.get(partialId);
    }

    // 部分匹配
    for (const [id, request] of this.pendingApprovals) {
      if (id.includes(partialId) || partialId.includes(id)) {
        return request;
      }
    }

    return undefined;
  }

  /**
   * 处理对话式审批决定
   * @param decision 用户决定 (y/yes/同意/是/n/no/拒绝/否)
   * @param approvalIdPartial 可选的审批ID（部分即可）
   * @returns 处理结果消息
   */
  async handleConversationalApproval(
    decision: string,
    approvalIdPartial: string = ""
  ): Promise<string> {
    const normalizedDecision = decision.toLowerCase().trim();
    
    // 解析用户决定
    const isApproved = ['y', 'yes', '同意', '是', 'approve', 'approved'].includes(normalizedDecision);
    const isRejected = ['n', 'no', '拒绝', '否', 'reject', 'rejected', 'deny', 'denied'].includes(normalizedDecision);
    
    if (!isApproved && !isRejected) {
      return `❌ 无效的审批决定: "${decision}"。请输入 'y'/'yes'/'同意'/'是' 批准，或 'n'/'no'/'拒绝'/'否' 拒绝。`;
    }

    // 查找审批请求
    const request = this.findApprovalByPartialId(approvalIdPartial);
    if (!request) {
      const waitingCount = Array.from(this.pendingApprovals.values()).filter(r => !r.resolved).length;
      return waitingCount > 0
        ? `❌ 找不到匹配的审批请求。当前有 ${waitingCount} 个待处理的审批。`
        : '❌ 没有找到待审批的请求。';
    }

    if (request.resolved) {
      return `❌ 审批请求 ${request.approvalId.slice(-8)} 已经被处理过了。`;
    }

    // 标记为已解决
    request.resolved = true;
    const decisionText = isApproved ? '✅ 批准' : '❌ 拒绝';

    if (isApproved) {
      return `${decisionText} - 前端动作 "${request.actionName}" 已获批准，正在执行...`;
    } else {
      return `${decisionText} - 前端动作 "${request.actionName}" 已被拒绝，操作已取消。`;
    }
  }

  /**
   * 等待审批结果
   * @param approvalId 审批ID
   * @param timeoutMs 超时时间（毫秒）
   * @returns Promise<ApprovalDecision> 审批结果
   */
  async waitForApproval(approvalId: string, timeoutMs: number = 30000): Promise<ApprovalDecision> {
    const request = this.pendingApprovals.get(approvalId);
    if (!request) {
      throw new Error(`审批请求 ${approvalId} 不存在`);
    }

    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const checkInterval = 500; // 每500ms检查一次

      const checkApproval = () => {
        const currentRequest = this.pendingApprovals.get(approvalId);
        
        if (currentRequest?.resolved) {
          // 通过检查最近的审批消息来判断结果
          // 这里需要与对话系统集成来获取用户的实际决定
          resolve('approved'); // 默认为批准，实际应该从对话系统获取
          return;
        }

        if (Date.now() - startTime > timeoutMs) {
          reject(new Error(`审批请求 ${approvalId} 超时`));
          return;
        }

        setTimeout(checkApproval, checkInterval);
      };

      checkApproval();
    });
  }

  /**
   * 获取所有待审批请求
   */
  getPendingApprovals(): FrontendApprovalRequest[] {
    return Array.from(this.pendingApprovals.values()).filter(req => !req.resolved);
  }

  /**
   * 清理已解决的审批请求（可选：保留最近的一些记录）
   */
  cleanup(keepRecentCount: number = 10): void {
    const resolved = Array.from(this.pendingApprovals.entries())
      .filter(([_, req]) => req.resolved)
      .sort((a, b) => new Date(b[1].timestamp).getTime() - new Date(a[1].timestamp).getTime());

    // 保留最近的记录，删除其余的
    resolved.slice(keepRecentCount).forEach(([id, _]) => {
      this.pendingApprovals.delete(id);
    });
  }

  /**
   * 生成审批提示消息
   */
  generateApprovalMessage(request: FrontendApprovalRequest): string {
    const paramsText = Object.keys(request.parameters).length > 0 
      ? `\n参数: ${JSON.stringify(request.parameters, null, 2)}`
      : '';

    return `🔐 **前端动作审批请求**
      
动作名称: ${request.actionName}${paramsText}
审批ID: ${request.approvalId.slice(-8)}
时间: ${new Date(request.timestamp).toLocaleString()}

请回复 'y' 或 '同意' 批准此操作，或 'n' 或 '拒绝' 取消操作。

⚠️ **重要**: 当你批准或拒绝时，请使用审批ID "${request.approvalId.slice(-8)}" 来确保正确处理。`;
  }
}