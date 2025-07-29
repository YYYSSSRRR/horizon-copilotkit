// 基础类型定义

export interface PlaywrightExecutionEngineOptions {
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
  timeout?: number;
}

export interface TestResult {
  name: string;
  success: boolean;
  duration: number;
  error?: Error;
}

export interface ScriptExecutionResult {
  success: boolean;
  duration: number;
  results: TestResult[];
}

export interface LocatorOptions {
  hasText?: string;
  hasNotText?: string;
  timeout?: number;
}

export interface ElementWaitOptions {
  state?: 'attached' | 'detached' | 'visible' | 'hidden';
  timeout?: number;
}

export interface ClickOptions {
  button?: 'left' | 'right' | 'middle';
  clickCount?: number;
  delay?: number;
  position?: { x: number; y: number };
  modifiers?: Array<'Alt' | 'Control' | 'Meta' | 'Shift'>;
  force?: boolean;
  noWaitAfter?: boolean;
  timeout?: number;
}

export interface FillOptions {
  force?: boolean;
  noWaitAfter?: boolean;
  timeout?: number;
}

export interface TypeOptions {
  delay?: number;
  noWaitAfter?: boolean;
  timeout?: number;
}

export interface SelectOptionValues {
  value?: string;
  label?: string;
  index?: number;
}

export interface ExpectMatcherOptions {
  timeout?: number;
  useInnerText?: boolean;
}

export interface PageGotoOptions {
  waitUntil?: 'load' | 'domcontentloaded' | 'networkidle';
  timeout?: number;
  referer?: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ViewportSize {
  width: number;
  height: number;
}

// DOM 相关类型
export interface DOMRect {
  x: number;
  y: number;
  width: number;
  height: number;
  top: number;
  right: number;
  bottom: number;
  left: number;
}

// 事件模拟相关类型
export interface KeyboardOptions {
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
}

export interface MouseEventOptions {
  button?: number;
  buttons?: number;
  clientX?: number;
  clientY?: number;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
}

// 日志相关类型
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface Logger {
  debug(message: string, ...args: any[]): void;
  info(message: string, ...args: any[]): void;
  warn(message: string, ...args: any[]): void;
  error(message: string, ...args: any[]): void;
  success(message: string, ...args: any[]): void;
}