/// <reference path="../types/global.d.ts" />
import type { 
  ClickOptions, 
  FillOptions, 
  TypeOptions,
  BoundingBox,
  ViewportSize,
  Logger 
} from '../../types/index.js';
import { 
  getRoleSelector, 
  buildGetByTextSelector,
  buildGetByLabelSelector, 
  buildGetByPlaceholderSelector,
  buildGetByTestIdSelector,
  buildGetByTitleSelector,
  type RoleOptions 
} from '../utils/role-selector-utils.js';

/**
 * 页面上下文接口 - 统一 Page 和 Frame 的操作环境
 */
export interface PageContext {
  readonly document: Document;
  readonly window: Window;
}

/**
 * 基础页面操作类 - Page 和 Frame 的共同基类
 */
export abstract class BasePageContext {
  protected readonly logger: Logger;
  protected abstract getContext(): PageContext;

  constructor() {
    this.logger = new (window.PlaywrightLogger || (console as any))() as Logger;
  }

  // =============== 基本信息方法 ===============

  /**
   * 获取标题
   */
  async title(): Promise<string> {
    return this.getContext().document.title;
  }

  /**
   * 获取内容
   */
  async content(): Promise<string> {
    return this.getContext().document.documentElement.outerHTML;
  }

  // =============== 元素交互方法 ===============

  /**
   * 等待元素
   */
  async waitForSelector(selector: string, options: { timeout?: number; state?: string } = {}): Promise<Element> {
    const { timeout = 30000 } = options;
    return await this.waitForElementInContext(selector, timeout);
  }

  /**
   * 点击元素
   */
  async click(selector: string, _options?: ClickOptions): Promise<void> {
    const element = await this.waitForSelector(selector);
    const context = this.getContext();
    
    const clickEvent = new (context.window as any).Event('click', {
      bubbles: true,
      cancelable: true
    });
    
    element.dispatchEvent(clickEvent);
    this.logger.debug(`Clicked: ${selector}`);
  }

  /**
   * 双击元素
   */
  async dblclick(selector: string, _options?: ClickOptions): Promise<void> {
    const element = await this.waitForSelector(selector);
    const context = this.getContext();
    
    const dblClickEvent = new (context.window as any).MouseEvent('dblclick', {
      bubbles: true,
      cancelable: true
    });
    
    element.dispatchEvent(dblClickEvent);
    this.logger.debug(`Double clicked: ${selector}`);
  }

  /**
   * 填充表单
   */
  async fill(selector: string, value: string, _options?: FillOptions): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement | HTMLTextAreaElement;
    const context = this.getContext();
    
    // 检查元素是否可以填充 - 对于测试环境中的 mock，只检查是否有 value 属性
    if (!('value' in element)) {
      throw new Error(`Element is not fillable: ${selector}`);
    }

    // 清空现有值
    (element as any).value = '';
    // 设置新值
    (element as any).value = value;

    // 触发 input 和 change 事件
    const inputEvent = new (context.window as any).Event('input', {
      bubbles: true,
      cancelable: true
    });
    const changeEvent = new (context.window as any).Event('change', {
      bubbles: true,
      cancelable: true
    });

    element.dispatchEvent(inputEvent);
    element.dispatchEvent(changeEvent);
    
    this.logger.debug(`填充: ${selector} = "${value}"`);
  }

  /**
   * 输入文本
   */
  async type(selector: string, text: string, options: TypeOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector);
    const context = this.getContext();
    const delay = options.delay || 0;

    // 聚焦元素
    (element as HTMLElement).focus();

    // 逐字符输入
    for (const char of text) {
      const keydownEvent = new (context.window as any).KeyboardEvent('keydown', {
        key: char,
        bubbles: true,
        cancelable: true
      });
      const keyupEvent = new (context.window as any).KeyboardEvent('keyup', {
        key: char,
        bubbles: true,
        cancelable: true
      });

      element.dispatchEvent(keydownEvent);
      
      if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
        element.value += char;
        
        const inputEvent = new (context.window as any).Event('input', {
          bubbles: true,
          cancelable: true
        });
        element.dispatchEvent(inputEvent);
      }

      element.dispatchEvent(keyupEvent);

      if (delay > 0) {
        await this.waitForTimeout(delay);
      }
    }
    
    this.logger.debug(`Typed: ${selector} -> "${text}"`);
  }

  /**
   * 按键操作
   */
  async press(selector: string, key: string, _options?: TypeOptions): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLElement;
    const context = this.getContext();
    
    element.focus();
    
    const keyEvent = new (context.window as any).KeyboardEvent('keydown', {
      key: key,
      bubbles: true,
      cancelable: true
    });
    
    element.dispatchEvent(keyEvent);
    this.logger.debug(`Pressed key: ${selector} -> ${key}`);
  }

  /**
   * 悬停
   */
  async hover(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector);
    const context = this.getContext();
    
    const mouseOverEvent = new (context.window as any).MouseEvent('mouseover', {
      bubbles: true,
      cancelable: true
    });

    element.dispatchEvent(mouseOverEvent);
    this.logger.debug(`Hovered: ${selector}`);
  }

  /**
   * 选择复选框
   */
  async check(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement;
    const context = this.getContext();
    
    if (element.type === 'checkbox' || element.type === 'radio') {
      element.checked = true;
      element.dispatchEvent(new (context.window as any).Event('change', { bubbles: true }));
      this.logger.debug(`选择: ${selector}`);
    }
  }

  /**
   * 取消选择复选框
   */
  async uncheck(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement;
    const context = this.getContext();
    
    if (element.type === 'checkbox') {
      element.checked = false;
      element.dispatchEvent(new (context.window as any).Event('change', { bubbles: true }));
      this.logger.debug(`取消选择: ${selector}`);
    }
  }

  /**
   * 选择下拉选项
   */
  async selectOption(selector: string, values: string | string[]): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLSelectElement;
    const context = this.getContext();
    
    if (element.tagName === 'SELECT') {
      if (Array.isArray(values)) {
        Array.from(element.options).forEach(option => {
          option.selected = values.includes(option.value) || values.includes(option.text);
        });
      } else {
        element.value = values;
      }
      element.dispatchEvent(new (context.window as any).Event('change', { bubbles: true }));
      this.logger.debug(`Selected option: ${selector} = ${values}`);
    }
  }

  /**
   * 聚焦元素
   */
  async focus(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLElement;
    await this.scrollIntoViewIfNeeded(element);
    
    element.focus();
    this.logger.debug(`聚焦: ${selector}`);
  }

  // =============== 脚本执行方法 ===============

  /**
   * 在上下文中执行脚本
   */
  async evaluate<T>(fn: (...args: any[]) => T, ...args: any[]): Promise<T> {
    const context = this.getContext();
    try {
      return fn.apply(context.window, args);
    } catch (error) {
      this.logger.error('Script execution failed:', error);
      throw error;
    }
  }

  /**
   * 在上下文中执行脚本并返回句柄
   */
  async evaluateHandle<T>(fn: (...args: any[]) => T, ...args: any[]): Promise<T> {
    return this.evaluate(fn, ...args);
  }

  // =============== 元素信息获取方法 ===============

  /**
   * 获取元素文本内容
   */
  async textContent(selector: string): Promise<string | null> {
    const element = await this.waitForSelector(selector);
    return element.textContent;
  }

  /**
   * 获取元素内部 HTML
   */
  async innerHTML(selector: string): Promise<string> {
    const element = await this.waitForSelector(selector);
    return element.innerHTML;
  }

  /**
   * 获取元素属性
   */
  async getAttribute(selector: string, name: string): Promise<string | null> {
    const element = await this.waitForSelector(selector);
    return element.getAttribute(name);
  }

  /**
   * 检查元素是否可见
   */
  async isVisible(selector: string): Promise<boolean> {
    try {
      const element = await this.waitForSelector(selector);
      const context = this.getContext();
      const style = context.window.getComputedStyle(element as HTMLElement);
      return style.display !== 'none' && 
             style.visibility !== 'hidden' && 
             style.opacity !== '0';
    } catch (error) {
      return false;
    }
  }

  /**
   * 获取元素边界框
   */
  async boundingBox(selector: string): Promise<BoundingBox> {
    const element = await this.waitForSelector(selector);
    const context = this.getContext();
    const rect = element.getBoundingClientRect();
    
    return {
      x: rect.left + context.window.scrollX,
      y: rect.top + context.window.scrollY,
      width: rect.width,
      height: rect.height
    };
  }

  /**
   * 获取视口大小
   */
  viewportSize(): ViewportSize {
    const context = this.getContext();
    return { 
      width: context.window.innerWidth, 
      height: context.window.innerHeight 
    };
  }

  // =============== 辅助方法 ===============

  /**
   * 等待超时
   */
  async waitForTimeout(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 等待函数条件
   */
  async waitForFunction<T>(fn: () => T, options: { timeout?: number } = {}): Promise<T> {
    const { timeout = 30000 } = options;
    const startTime = Date.now();
    const interval = 100;
    const context = this.getContext();

    while (Date.now() - startTime < timeout) {
      try {
        const result = fn.call(context.window);
        if (result) {
          return result;
        }
      } catch (error) {
        // 继续等待
      }
      await this.waitForTimeout(interval);
    }
    
    throw new Error('waitForFunction timeout');
  }

  /**
   * 滚动元素到可视区域
   */
  async scrollIntoViewIfNeeded(element: Element): Promise<void> {
    const rect = element.getBoundingClientRect();
    const context = this.getContext();
    const isInViewport = rect.top >= 0 && rect.bottom <= context.window.innerHeight &&
                        rect.left >= 0 && rect.right <= context.window.innerWidth;
    
    if (!isInViewport) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await this.waitForTimeout(100);
      this.logger.debug('Element scrolled into view');
    }
  }

  // =============== 现代定位器方法 ===============

  /**
   * 创建 Locator
   */
  locator(selector: string, options: Record<string, any> = {}): any {
    const LocatorAdapterClass = window.PlaywrightLocatorAdapter;
    if (!LocatorAdapterClass) {
      throw new Error('PlaywrightLocatorAdapter not found in global scope');
    }
    return new LocatorAdapterClass(selector, this, options);
  }

  /**
   * 根据角色定位
   */
  getByRole(role: string, options: { name?: string; exact?: boolean; level?: number } = {}): any {
    const { name, exact = false, level } = options;
    const roleOptions: RoleOptions = { exact, level };
    
    if (name) {
      const baseSelector = getRoleSelector(role, roleOptions);
      return this.locator(baseSelector).filter({
        hasAccessibleName: name,
        exact: exact
      });
    }
    
    const baseSelector = getRoleSelector(role, roleOptions);
    return this.locator(baseSelector);
  }

  /**
   * 根据文本定位
   */
  getByText(text: string, options: { exact?: boolean } = {}): any {
    const { exact = false } = options;
    const selector = buildGetByTextSelector(text, exact);
    return this.locator(selector);
  }

  /**
   * 根据标签定位
   */
  getByLabel(text: string, options: { exact?: boolean } = {}): any {
    const { exact = false } = options;
    const selector = buildGetByLabelSelector(text, exact);
    return this.locator(selector);
  }

  /**
   * 根据占位符定位
   */
  getByPlaceholder(text: string, options: { exact?: boolean } = {}): any {
    const { exact = false } = options;
    const selector = buildGetByPlaceholderSelector(text, exact);
    return this.locator(selector);
  }

  /**
   * 根据测试 ID 定位
   */
  getByTestId(testId: string): any {
    const selector = buildGetByTestIdSelector(testId);
    return this.locator(selector);
  }

  /**
   * 根据标题定位
   */
  getByTitle(text: string, options: { exact?: boolean } = {}): any {
    const { exact = false } = options;
    const selector = buildGetByTitleSelector(text, exact);
    return this.locator(selector);
  }

  // =============== 抽象方法 ===============

  /**
   * 等待元素在上下文中出现
   */
  protected abstract waitForElementInContext(selector: string, timeout: number): Promise<Element>;
}