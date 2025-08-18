export interface MenuItem {
  id: string;
  text: string;
  url?: string;  // Make URL optional for function-based navigation
  level: number;
  parentId?: string;
  hasSubmenu: boolean;
  elementSelector?: string;
  // New fields for function-based navigation
  emit?: string[];
}


export interface MenuConfig {
  baseUrl?: string;
  loginConfig?: LoginConfig;
  menuSelectors?: string[];
  excludePatterns?: string[];
  maxDepth?: number;
  waitTimeout?: number;
  // New fields for function-based menu handling
  functionBased?: FunctionBasedMenuConfig;
}

export interface LoginConfig {
  loginUrl: string;
  usernameSelector: string;
  passwordSelector: string;
  submitSelector: string;
  username: string;
  password: string;
  successSelector?: string;
}

export interface PageAnalysis {
  url: string;
  title: string;
  menuPath: string[];
  content: PageContent;
  timestamp: Date;
}


export interface PageContent {
  html: string;
  text: string;
  forms: FormInfo[];
  tables: TableInfo[];
  buttons: ButtonInfo[];
  links: LinkInfo[];
  images: ImageInfo[];
  metadata: PageMetadata;
}

export interface FormInfo {
  id?: string;
  action?: string;
  method?: string;
  fields: FormField[];
  purpose?: string;
}

export interface FormField {
  name?: string;
  type: string;
  label?: string;
  placeholder?: string;
  required: boolean;
  options?: string[];
}

export interface TableInfo {
  id?: string;
  headers: string[];
  rowCount: number;
  hasActions: boolean;
  purpose?: string;
}

export interface ButtonInfo {
  text: string;
  type?: string;
  purpose?: string;
  action?: string;
}

export interface LinkInfo {
  text: string;
  href: string;
  isInternal: boolean;
}

export interface ImageInfo {
  src: string;
  alt?: string;
  purpose?: string;
}

export interface PageMetadata {
  description?: string;
  keywords?: string[];
  breadcrumbs: string[];
  pageType?: string;
}

export interface LLMAnalysisRequest {
  menuItem: MenuItem;
  pageContent: PageContent;
  context?: string;
}

export interface MenuFunctionality {
  menuId: string;
  menuName: string;
  menuPath: string;
  url: string;
  primaryFunction: string;
  capabilities: string[];
  businessScope: string;
  userActions: string[];
  dataManagement: DataManagementInfo;
  technicalDetails: TechnicalDetails;
  usageScenarios: string[];
  relatedModules: string[];
  confidence: number;
}

export interface DataManagementInfo {
  dataTypes: string[];
  operations: string[];
  integrations: string[];
}

export interface TechnicalDetails {
  componentTypes: string[];
  frameworks: string[];
  apis: string[];
}

export interface AnalysisConfig {
  llm: LLMConfig;
  crawler: CrawlerConfig;
  output: OutputConfig;
  // Optional callback for function-based menu navigation
  onMenuOpen?: (emit: string[]) => Promise<void>;
}

export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'deepseek' | 'custom';
  model: string;
  apiKey: string;
  baseUrl?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

export interface CrawlerConfig {
  concurrency: number;
  delay: number;
  retries: number;
  timeout: number;
  userAgent?: string;
  viewport?: { width: number; height: number };
}

export interface OutputConfig {
  format: 'json';
  outputPath: string;
  includeScreenshots?: boolean;
  includeRawContent?: boolean;
}