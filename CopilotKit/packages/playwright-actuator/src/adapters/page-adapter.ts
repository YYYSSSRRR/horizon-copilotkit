/// <reference path="../types/global.d.ts" />
import type { 
  ClickOptions, 
  FillOptions, 
  TypeOptions, 
  PageGotoOptions, 
  BoundingBox, 
  ViewportSize,
  Logger
} from '../../types/index.js';
import { 
  getRoleSelector, 
  buildRoleXPathWithName,
  buildGetByTextSelector,
  buildGetByLabelSelector, 
  buildGetByPlaceholderSelector,
  buildGetByTestIdSelector,
  buildGetByTitleSelector,
  type RoleOptions 
} from '../utils/role-selector-utils.js';

/**
 * Page 适配器 - 实现 Playwright Page API
 */
class PageAdapter {
  private readonly logger: Logger;
  private readonly waitManager: any; // TODO: Type this properly
  private readonly eventSimulator: any; // TODO: Type this properly

  constructor() {
    this.logger = new (window.PlaywrightLogger || (console as any))() as Logger;
    this.waitManager = new (window.PlaywrightWaitManager as any)();
    this.eventSimulator = new (window.PlaywrightEventSimulator as any)();
  }

  // =============== 导航方法 ===============

  /**
   * 导航到指定 URL
   */
  async goto(url: string, options: PageGotoOptions = {}): Promise<{ url: string; status: number }> {
    const { waitUntil = 'load', timeout = 30000 } = options;
    
    this.logger.info(`导航到: ${url}`);
    
    if (window.location.href !== url) {
      window.location.href = url;
      await this.waitForLoadState(waitUntil);
    }
    
    return { url: window.location.href, status: 200 };
  }

  /**
   * 后退
   */
  async goBack(options: { waitUntil?: 'load' | 'domcontentloaded' | 'networkidle' } = {}): Promise<void> {
    const { waitUntil = 'load' } = options;
    window.history.back();
    await this.waitForLoadState(waitUntil);
  }

  /**
   * 前进
   */
  async goForward(options: { waitUntil?: 'load' | 'domcontentloaded' | 'networkidle' } = {}): Promise<void> {
    const { waitUntil = 'load' } = options;
    window.history.forward();
    await this.waitForLoadState(waitUntil);
  }

  /**
   * 刷新页面
   */
  async reload(options: { waitUntil?: 'load' | 'domcontentloaded' | 'networkidle' } = {}): Promise<void> {
    const { waitUntil = 'load' } = options;
    window.location.reload();
    await this.waitForLoadState(waitUntil);
  }

  // =============== 页面信息获取 ===============

  /**
   * 获取当前 URL
   */
  url(): string {
    return window.location.href;
  }

  /**
   * 获取页面标题
   */
  async title(): Promise<string> {
    return document.title;
  }

  /**
   * 获取页面内容
   */
  async content(): Promise<string> {
    return document.documentElement.outerHTML;
  }

  // =============== 元素交互方法 ===============

  /**
   * 点击元素
   */
  async click(selector: string, options: ClickOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector);
    await this.scrollIntoViewIfNeeded(element);
    
    this.eventSimulator.simulateClick(element, options);
    this.logger.debug(`点击: ${selector}`);
  }

  /**
   * 双击元素
   */
  async dblclick(selector: string, options: ClickOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector);
    await this.scrollIntoViewIfNeeded(element);
    
    this.eventSimulator.simulateDoubleClick(element);
    this.logger.debug(`双击: ${selector}`);
  }

  /**
   * 填充表单
   */
  async fill(selector: string, value: string, options: FillOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement | HTMLTextAreaElement;
    await this.scrollIntoViewIfNeeded(element);
    
    // 清空并填充
    element.value = '';
    element.value = value;
    
    // 触发相关事件
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    
    this.logger.debug(`填充: ${selector} = "${value}"`);
  }

  /**
   * 按键操作
   */
  async press(selector: string, key: string, options: TypeOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLElement;
    element.focus();
    
    this.eventSimulator.simulateKeyPress(element, key, options);
    this.logger.debug(`按键: ${selector} -> ${key}`);
  }

  /**
   * 输入文本（模拟打字）
   */
  async type(selector: string, text: string, options: TypeOptions = {}): Promise<void> {
    const element = await this.waitForSelector(selector);
    await this.eventSimulator.simulateTyping(element, text, options);
    this.logger.debug(`输入: ${selector} -> "${text}"`);
  }

  /**
   * 悬停
   */
  async hover(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector);
    await this.scrollIntoViewIfNeeded(element);
    
    this.eventSimulator.simulateHover(element);
    this.logger.debug(`悬停: ${selector}`);
  }

  /**
   * 选择复选框
   */
  async check(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement;
    if (element.type === 'checkbox' || element.type === 'radio') {
      element.checked = true;
      element.dispatchEvent(new Event('change', { bubbles: true }));
      this.logger.debug(`选择: ${selector}`);
    }
  }

  /**
   * 取消选择复选框
   */
  async uncheck(selector: string): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLInputElement;
    if (element.type === 'checkbox') {
      element.checked = false;
      element.dispatchEvent(new Event('change', { bubbles: true }));
      this.logger.debug(`取消选择: ${selector}`);
    }
  }

  /**
   * 选择下拉选项
   */
  async selectOption(selector: string, values: string | string[], options: Record<string, any> = {}): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLSelectElement;
    if (element.tagName === 'SELECT') {
      if (Array.isArray(values)) {
        // 多选
        Array.from(element.options).forEach(option => {
          option.selected = values.includes(option.value) || values.includes(option.text);
        });
      } else {
        element.value = values;
      }
      element.dispatchEvent(new Event('change', { bubbles: true }));
      this.logger.debug(`选择选项: ${selector} = ${values}`);
    }
  }

  /**
   * 聚焦元素
   */
  async focus(selector: string, options: Record<string, any> = {}): Promise<void> {
    const element = await this.waitForSelector(selector) as HTMLElement;
    await this.scrollIntoViewIfNeeded(element);
    
    element.focus();
    this.logger.debug(`聚焦: ${selector}`);
  }

  // =============== 现代定位器方法 ===============

  /**
   * 创建 Locator
   */
  locator(selector: string, options: Record<string, any> = {}): any {
    // 动态获取 LocatorAdapter 类
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
      // 使用工具函数构建带名称匹配的 XPath
      const xpath = buildRoleXPathWithName(role, name, roleOptions);
      return this.locator(`xpath=${xpath}`);
    }
    
    // 获取基础角色选择器
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

  // =============== 等待方法 ===============

  /**
   * 等待元素
   */
  async waitForSelector(selector: string, options: { timeout?: number; state?: string } = {}): Promise<Element> {
    const { timeout = 30000, state = 'visible' } = options;
    
    // 如果是 xpath，需要特殊处理
    if (selector.startsWith('xpath=')) {
      return this.waitForXPath(selector.substring(6), { timeout });
    }
    
    // 处理 :visible 和 :hidden 伪类选择器
    let actualSelector = selector;
    let requiredState = state;
    
    if (selector.includes(':visible')) {
      actualSelector = selector.replace(':visible', '');
      requiredState = 'visible';
    } else if (selector.includes(':hidden')) {
      actualSelector = selector.replace(':hidden', '');
      requiredState = 'hidden';
    }
    
    const element = await this.waitManager.waitForElement(actualSelector, timeout);
    
    if (requiredState === 'visible') {
      await this.waitManager.waitForCondition(
        () => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && 
                 style.visibility !== 'hidden' && style.display !== 'none';
        },
        timeout,
        `元素 "${actualSelector}" 等待可见超时`
      );
    } else if (requiredState === 'hidden') {
      await this.waitManager.waitForCondition(
        () => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return rect.width === 0 || rect.height === 0 || 
                 style.visibility === 'hidden' || style.display === 'none';
        },
        timeout,
        `元素 "${actualSelector}" 等待隐藏超时`
      );
    }
    
    return element;
  }

  /**
   * 等待 XPath 元素
   */
  async waitForXPath(xpath: string, options: { timeout?: number } = {}): Promise<Element> {
    const { timeout = 30000 } = options;
    
    return this.waitManager.waitForCondition(
      () => {
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        return result.singleNodeValue;
      },
      timeout,
      `XPath 元素等待超时: ${xpath}`
    );
  }

  /**
   * 等待超时
   */
  async waitForTimeout(ms: number): Promise<void> {
    return this.waitManager.waitForTimeout(ms);
  }

  /**
   * 等待函数
   */
  async waitForFunction<T>(fn: () => T, arg?: any, options: { timeout?: number } = {}): Promise<T> {
    const { timeout = 30000 } = options;
    return this.waitManager.waitForCondition(
      () => fn(),
      timeout,
      '等待函数条件超时'
    );
  }

  /**
   * 等待 URL
   */
  async waitForURL(url: string | RegExp, options: { timeout?: number } = {}): Promise<void> {
    const { timeout = 30000 } = options;
    return this.waitManager.waitForURL(url, timeout);
  }

  /**
   * 等待加载状态
   */
  async waitForLoadState(state: 'load' | 'domcontentloaded' | 'networkidle' = 'load'): Promise<void> {
    return this.waitManager.waitForLoadState(state);
  }

  // =============== 脚本执行方法 ===============

  /**
   * 在页面上下文中执行脚本
   */
  async evaluate<T>(fn: (...args: any[]) => T, ...args: any[]): Promise<T> {
    try {
      return fn.apply(window, args);
    } catch (error) {
      this.logger.error('脚本执行失败:', error);
      throw error;
    }
  }

  /**
   * 在页面上下文中执行脚本并返回句柄
   */
  async evaluateHandle<T>(fn: (...args: any[]) => T, ...args: any[]): Promise<T> {
    return this.evaluate(fn, ...args);
  }

  /**
   * 添加脚本标签
   */
  async addScriptTag(options: { url?: string; path?: string; content?: string; type?: string } = {}): Promise<HTMLScriptElement> {
    const { url, path, content, type = 'text/javascript' } = options;
    
    const script = document.createElement('script');
    script.type = type;
    
    if (url) {
      script.src = url;
    } else if (content) {
      script.textContent = content;
    }
    
    document.head.appendChild(script);
    
    // 等待脚本加载
    if (url) {
      await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = reject;
      });
    }
    
    this.logger.debug('添加脚本标签');
    return script;
  }

  /**
   * 添加样式标签
   */
  async addStyleTag(options: { url?: string; path?: string; content?: string } = {}): Promise<HTMLLinkElement | HTMLStyleElement> {
    const { url, path, content } = options;
    
    if (url) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      document.head.appendChild(link);
      return link;
    } else if (content) {
      const style = document.createElement('style');
      style.textContent = content;
      document.head.appendChild(style);
      return style;
    }

    throw new Error('Either url or content must be provided');
  }

  // =============== 辅助方法 ===============

  /**
   * 滚动元素到可视区域
   */
  async scrollIntoViewIfNeeded(element: Element): Promise<void> {
    const rect = element.getBoundingClientRect();
    const isInViewport = rect.top >= 0 && rect.bottom <= window.innerHeight &&
                        rect.left >= 0 && rect.right <= window.innerWidth;
    
    if (!isInViewport) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await this.waitForTimeout(100); // 等待滚动完成
      this.logger.debug('元素滚动到可视区域');
    }
  }

  /**
   * 获取元素边界框
   */
  async boundingBox(selector: string): Promise<BoundingBox> {
    const element = await this.waitForSelector(selector);
    const rect = element.getBoundingClientRect();
    
    return {
      x: rect.left + window.scrollX,
      y: rect.top + window.scrollY,
      width: rect.width,
      height: rect.height
    };
  }

  /**
   * 设置视口大小（有限支持）
   */
  async setViewportSize(size: ViewportSize): Promise<ViewportSize> {
    // 浏览器环境中无法直接设置视口大小
    // 这里只是记录日志
    this.logger.warn('浏览器环境中无法设置视口大小');
    return { width: window.innerWidth, height: window.innerHeight };
  }

  /**
   * 获取视口大小
   */
  viewportSize(): ViewportSize {
    return { width: window.innerWidth, height: window.innerHeight };
  }
}


// 导出给浏览器使用
if (typeof window !== 'undefined') {
  window.PlaywrightPageAdapter = PageAdapter;
}


// ES6 模块导出
export default PageAdapter;