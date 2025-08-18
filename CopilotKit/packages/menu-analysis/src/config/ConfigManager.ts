import { AnalysisConfig, MenuConfig, LLMConfig, CrawlerConfig, OutputConfig } from '../types';

export function createDefaultConfig(): AnalysisConfig {
  return {
    llm: {
      provider: 'deepseek',
      model: 'deepseek-chat',
      apiKey: process.env.DEEPSEEK_API_KEY || process.env.OPENAI_API_KEY || '',
      baseUrl: 'https://api.deepseek.com',
      temperature: 0.3,
      maxTokens: 2000
    },
    crawler: {
      concurrency: 3,
      delay: 1000,
      retries: 3,
      timeout: 30000,
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      viewport: { width: 1920, height: 1080 }
    },
    output: {
      format: 'json',
      outputPath: './menu-analysis-results',
      includeScreenshots: false,
      includeRawContent: false
    }
  };
}

export function createMenuConfig(baseUrl: string): MenuConfig {
  return {
    baseUrl,
    menuSelectors: [
      '[role="navigation"] a',
      '.menu a, .nav a',
      '.sidebar a',
      '.main-menu a',
      '.navigation a'
    ],
    excludePatterns: [
      'logout',
      'help',
      'javascript:',
      '#',
      'mailto:',
      'tel:'
    ],
    maxDepth: 3,
    waitTimeout: 30000
  };
}

export function validateConfig(config: AnalysisConfig): void {
  // Validate LLM config
  if (!config.llm.apiKey) {
    throw new Error('LLM API key is required');
  }

  if (!config.llm.model) {
    throw new Error('LLM model is required');
  }

  // Validate crawler config
  if (config.crawler.concurrency < 1 || config.crawler.concurrency > 10) {
    throw new Error('Crawler concurrency must be between 1 and 10');
  }

  if (config.crawler.delay < 0) {
    throw new Error('Crawler delay must be non-negative');
  }

  // Validate output config
  if (config.output.format !== 'json') {
    throw new Error('Output format must be json');
  }

  if (!config.output.outputPath) {
    throw new Error('Output path is required');
  }
}

export function loadConfigFromEnv(): Partial<AnalysisConfig> {
  return {
    llm: {
      provider: (process.env.LLM_PROVIDER as any) || 'deepseek',
      model: process.env.LLM_MODEL || 'deepseek-chat',
      apiKey: process.env.DEEPSEEK_API_KEY || process.env.OPENAI_API_KEY || process.env.LLM_API_KEY || '',
      baseUrl: process.env.LLM_BASE_URL || (process.env.LLM_PROVIDER === 'deepseek' ? 'https://api.deepseek.com' : undefined),
      temperature: process.env.LLM_TEMPERATURE ? parseFloat(process.env.LLM_TEMPERATURE) : 0.3,
      maxTokens: process.env.LLM_MAX_TOKENS ? parseInt(process.env.LLM_MAX_TOKENS) : 2000
    },
    crawler: {
      concurrency: process.env.CRAWLER_CONCURRENCY ? parseInt(process.env.CRAWLER_CONCURRENCY) : 3,
      delay: process.env.CRAWLER_DELAY ? parseInt(process.env.CRAWLER_DELAY) : 1000,
      retries: process.env.CRAWLER_RETRIES ? parseInt(process.env.CRAWLER_RETRIES) : 3,
      timeout: process.env.CRAWLER_TIMEOUT ? parseInt(process.env.CRAWLER_TIMEOUT) : 30000
    },
    output: {
      format: 'json',
      outputPath: process.env.OUTPUT_PATH || './menu-analysis-results',
      includeScreenshots: process.env.INCLUDE_SCREENSHOTS === 'true',
      includeRawContent: process.env.INCLUDE_RAW_CONTENT === 'true'
    }
  };
}

export function mergeConfigs(base: AnalysisConfig, override: Partial<AnalysisConfig>): AnalysisConfig {
  return {
    llm: { ...base.llm, ...override.llm },
    crawler: { ...base.crawler, ...override.crawler },
    output: { ...base.output, ...override.output }
  };
}