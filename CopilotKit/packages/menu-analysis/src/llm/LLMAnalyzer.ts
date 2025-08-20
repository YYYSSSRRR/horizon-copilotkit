import OpenAI from 'openai';
import { HttpsProxyAgent } from 'https-proxy-agent';
import { LLMConfig, PageAnalysis, MenuFunctionality, MenuItem, LLMAnalysisRequest } from '../types';
import { Logger } from '../utils/Logger';

export class LLMAnalyzer {
  private client: OpenAI;
  private config: LLMConfig;
  private logger: Logger;
  private proxyAgent?: HttpsProxyAgent;

  constructor(config: LLMConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;

    // 华为企业代理配置
    this.setupProxy();

    // DeepSeek API configuration
    const baseURL = config.baseUrl ||
      (config.provider === 'deepseek' ? 'https://api.deepseek.com' : 'https://api.openai.com/v1');

    // Create OpenAI client with proxy support
    const clientConfig: any = {
      apiKey: config.apiKey,
      baseURL
    };

    // Add proxy agent if configured
    if (this.proxyAgent) {
      clientConfig.httpAgent = this.proxyAgent;
      clientConfig.httpsAgent = this.proxyAgent;
    }

    this.client = new OpenAI(clientConfig);

    this.logger.info('LLMAnalyzer initialized', {
      provider: config.provider,
      model: config.model,
      baseURL,
      proxyEnabled: !!this.proxyAgent
    });
  }

  private setupProxy(): void {
    try {
      // 从环境变量读取华为企业代理配置
      const HUAWEI_PROXY = process.env.HUAWEI_PROXY || process.env.HTTP_PROXY || process.env.HTTPS_PROXY;

      if (!HUAWEI_PROXY) {
        this.logger.info('No proxy configuration found in environment variables');
        this.proxyAgent = undefined;
        return;
      }

      // 设置代理环境变量（如果尚未设置）
      if (!process.env.HTTP_PROXY) {
        process.env.HTTP_PROXY = HUAWEI_PROXY;
      }
      if (!process.env.HTTPS_PROXY) {
        process.env.HTTPS_PROXY = HUAWEI_PROXY;
      }

      // 设置不使用代理的地址
      const noProxy = process.env.NO_PROXY || 'localhost,127.0.0.1,.huawei.com';
      process.env.NO_PROXY = noProxy;

      // 是否禁用 SSL 验证（从环境变量读取，默认禁用）
      const rejectUnauthorized = process.env.NODE_TLS_REJECT_UNAUTHORIZED !== '0';
      if (process.env.DISABLE_SSL_VERIFY === 'true' || process.env.NODE_TLS_REJECT_UNAUTHORIZED === undefined) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
      }

      // 创建支持华为代理的 HTTPS Agent
      this.proxyAgent = new HttpsProxyAgent(HUAWEI_PROXY, {
        rejectUnauthorized: !rejectUnauthorized,
        timeout: parseInt(process.env.PROXY_TIMEOUT || '60000'),
        keepAlive: true
      });

      this.logger.info('Proxy configuration applied', {
        proxy: this.maskProxyUrl(HUAWEI_PROXY),
        noProxy,
        sslVerification: rejectUnauthorized,
        timeout: parseInt(process.env.PROXY_TIMEOUT || '60000')
      });

    } catch (error) {
      this.logger.warn('Failed to setup proxy configuration:', error);
      // Continue without proxy if setup fails
      this.proxyAgent = undefined;
    }
  }

  /**
   * 遮掩代理URL中的敏感信息
   */
  private maskProxyUrl(proxyUrl: string): string {
    try {
      const url = new URL(proxyUrl);
      if (url.username) {
        // 只显示用户名的前3个字符，密码完全遮掩
        const maskedUsername = url.username.substring(0, 3) + '*'.repeat(Math.max(0, url.username.length - 3));
        const maskedPassword = url.password ? '*'.repeat(url.password.length) : '';
        return `${url.protocol}//${maskedUsername}:${maskedPassword}@${url.host}`;
      }
      return proxyUrl;
    } catch {
      return proxyUrl.replace(/\/\/[^@]+@/, '//***:***@');
    }
  }

  async analyzeMenuFunctionality(request: LLMAnalysisRequest): Promise<MenuFunctionality> {
    this.logger.info(`Analyzing functionality for menu: ${request.menuItem.text}`);

    const prompt = this.buildAnalysisPrompt(request);

    try {
      // Prepare request options
      const requestOptions: any = {
        model: this.config.model,
        messages: [
          {
            role: 'system',
            content: this.getSystemPrompt()
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: this.config.temperature || 0.3,
        max_tokens: this.config.maxTokens || 2000
      };

      // DeepSeek doesn't support response_format parameter yet
      if (this.config.provider !== 'deepseek') {
        requestOptions.response_format = { type: 'json_object' };
      }

      const response = await this.client.chat.completions.create(requestOptions);

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response content received from LLM');
      }

      // For DeepSeek, we need to extract JSON from the response
      let analysis: MenuFunctionality;
      try {
        if (this.config.provider === 'deepseek') {
          // Extract JSON from markdown code blocks or direct JSON
          const jsonMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/) ||
                           content.match(/(\{[\s\S]*\})/);
          const jsonStr = jsonMatch ? jsonMatch[1] : content;
          analysis = JSON.parse(jsonStr) as MenuFunctionality;
        } else {
          analysis = JSON.parse(content) as MenuFunctionality;
        }
      } catch (parseError) {
        this.logger.warn(`Failed to parse LLM response as JSON: ${parseError}`, { content });
        throw new Error(`Invalid JSON response from LLM: ${parseError}`);
      }

      // Ensure required fields and add metadata
      analysis.id = request.menuItem.id;
      analysis.name = request.menuItem.text;
      analysis.emit = request.menuItem.emit || '';

      this.logger.info(`Successfully analyzed menu: ${request.menuItem.text}`);
      return analysis;

    } catch (error) {
      this.logger.error(`Failed to analyze menu ${request.menuItem.text}:`, error);

      // Return fallback analysis
      return this.createFallbackAnalysis(request.menuItem, request.pageContent);
    }
  }

  private getSystemPrompt(): string {
    return this.config.systemPrompt || `
你是一个专业的系统功能分析师，擅长分析网页内容并总结菜单功能。你需要基于提供的页面内容，生成结构化的菜单功能描述。

请严格按照以下JSON格式返回分析结果：

{
  "id": "菜单ID",
  "name": "菜单名称",
  "primaryFunction": "主要功能"
}

分析要求：
1. 基于页面的表单、表格、按钮等元素推断功能
2. 从页面标题、文本内容理解业务背景
3. 识别用户可能的操作流程
4. 提供简洁明确的功能描述

请确保返回有效的JSON格式。
    `.trim();
  }

  private buildAnalysisPrompt(request: LLMAnalysisRequest): string {
    const { menuItem, pageContent } = request;

    return `
请分析以下菜单功能：

## 菜单信息
- 菜单名称: ${menuItem.text}
- 菜单层级: ${menuItem.level}
- 页面URL: ${menuItem.url}
- 菜单路径: ${request.context || ''}

## 页面内容分析

### 页面基本信息
- 页面标题: ${pageContent.metadata?.description || 'N/A'}
- 页面类型: ${pageContent.metadata?.pageType || 'N/A'}
- 面包屑: ${pageContent.metadata?.breadcrumbs?.join(' > ') || 'N/A'}

### 表单分析 (${pageContent.forms?.length || 0}个表单)
${this.formatForms(pageContent.forms || [])}

### 表格分析 (${pageContent.tables?.length || 0}个表格)
${this.formatTables(pageContent.tables || [])}

### 按钮操作 (${pageContent.buttons?.length || 0}个按钮)
${this.formatButtons(pageContent.buttons || [])}

### 页面文本内容（前500字符）
${pageContent.text?.substring(0, 500) || 'N/A'}

请基于以上信息，分析该菜单的功能并返回JSON格式的结果。
    `.trim();
  }

  private formatForms(forms: any[]): string {
    if (forms.length === 0) return '无表单';

    return forms.map((form, index) => {
      const fields = form.fields?.map((f: any) => `${f.label || f.name || f.type}`).join(', ') || '无字段';
      return `表单${index + 1}: ${form.purpose || '未知用途'} - 字段: ${fields}`;
    }).join('\n');
  }

  private formatTables(tables: any[]): string {
    if (tables.length === 0) return '无表格';

    return tables.map((table, index) => {
      const headers = table.headers?.join(', ') || '无表头';
      return `表格${index + 1}: ${table.purpose || '数据展示'} - 列: ${headers} - 行数: ${table.rowCount} - 有操作: ${table.hasActions ? '是' : '否'}`;
    }).join('\n');
  }

  private formatButtons(buttons: any[]): string {
    if (buttons.length === 0) return '无按钮';

    const buttonsByPurpose = buttons.reduce((acc: any, btn) => {
      const purpose = btn.purpose || 'action';
      acc[purpose] = (acc[purpose] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(buttonsByPurpose)
      .map(([purpose, count]) => `${purpose}: ${count}个`)
      .join(', ');
  }

  private createFallbackAnalysis(menuItem: MenuItem, pageContent: any): MenuFunctionality {
    // Create a basic analysis when LLM fails
    const hasForm = (pageContent.forms?.length || 0) > 0;
    const hasTable = (pageContent.tables?.length || 0) > 0;
    const buttonCount = pageContent.buttons?.length || 0;

    let primaryFunction = '信息展示';

    if (hasForm && hasTable) {
      primaryFunction = '数据管理';
    } else if (hasForm) {
      primaryFunction = '数据录入';
    } else if (hasTable) {
      primaryFunction = '数据查询';
    }

    if (buttonCount > 0) {
      primaryFunction += ' - 可交互操作';
    }

    return {
      id: menuItem.id,
      name: menuItem.text,
      primaryFunction,
      emit: menuItem.emit
    };
  }

  async batchAnalyze(requests: LLMAnalysisRequest[]): Promise<MenuFunctionality[]> {
    const results: MenuFunctionality[] = [];
    const batchSize = 5; // Process in small batches to avoid rate limits

    this.logger.info(`Starting batch analysis of ${requests.length} menus...`);

    for (let i = 0; i < requests.length; i += batchSize) {
      const batch = requests.slice(i, i + batchSize);

      this.logger.info(`Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(requests.length / batchSize)}`);

      const batchPromises = batch.map(request =>
        this.analyzeMenuFunctionality(request).catch(error => {
          this.logger.error(`Failed to analyze ${request.menuItem.text}:`, error);
          return this.createFallbackAnalysis(request.menuItem, request.pageContent);
        })
      );

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);

      // Add delay between batches to respect rate limits
      if (i + batchSize < requests.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    this.logger.info(`Completed batch analysis. Processed ${results.length} menus.`);
    return results;
  }
}