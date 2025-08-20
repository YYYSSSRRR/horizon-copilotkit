import OpenAI from 'openai';
import { LLMConfig, PageAnalysis, MenuFunctionality, MenuItem, LLMAnalysisRequest } from '../types';
import { Logger } from '../utils/Logger';

export class LLMAnalyzer {
  private client: OpenAI;
  private config: LLMConfig;
  private logger: Logger;

  constructor(config: LLMConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    
    // DeepSeek API configuration
    const baseURL = config.baseUrl || 
      (config.provider === 'deepseek' ? 'https://api.deepseek.com' : 'https://api.openai.com/v1');
    
    this.client = new OpenAI({
      apiKey: config.apiKey,
      baseURL
    });
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
      analysis.menuId = request.menuItem.id;
      analysis.menuName = request.menuItem.text;
      analysis.url = request.menuItem.url || '';
      analysis.confidence = analysis.confidence || 0.8;

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
  "menuId": "菜单ID",
  "menuName": "菜单名称",
  "menuPath": "菜单路径",
  "url": "页面URL",
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
    const capabilities: string[] = [];

    if (hasForm && hasTable) {
      primaryFunction = '数据管理';
      capabilities.push('数据查询', '数据维护');
    } else if (hasForm) {
      primaryFunction = '数据录入';
      capabilities.push('数据新增', '数据编辑');
    } else if (hasTable) {
      primaryFunction = '数据查询';
      capabilities.push('数据展示', '数据查询');
    }

    if (buttonCount > 0) {
      capabilities.push('用户操作');
    }

    return {
      menuId: menuItem.id,
      menuName: menuItem.text,
      menuPath: '',
      url: menuItem.url || '',
      primaryFunction,
      capabilities,
      businessScope: '基于页面内容推断',
      userActions: capabilities,
      dataManagement: {
        dataTypes: ['未知'],
        operations: capabilities,
        integrations: []
      },
      technicalDetails: {
        componentTypes: [],
        frameworks: [],
        apis: []
      },
      usageScenarios: ['日常业务操作'],
      relatedModules: [],
      confidence: 0.5
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