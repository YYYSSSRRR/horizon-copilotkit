/// <reference path="../types/global.d.ts" />
import type { 
  ClickOptions, 
  FillOptions, 
  TypeOptions, 
  LocatorOptions, 
  ElementWaitOptions,
  Logger 
} from '../../types/index.js';
import { getReactAdapter } from '../framework-adapters/react-adapter.js';
import { getOpenInulaAdapter } from '../framework-adapters/openinula-adapter.js';
import { 
  getRoleSelector, 
  elementMatchesText, 
  elementMatchesAccessibleName,
  buildGetByTextSelector,
  buildGetByLabelSelector,
  buildGetByPlaceholderSelector,
  buildGetByTestIdSelector,
  buildGetByTitleSelector,
  type RoleOptions 
} from '../utils/role-selector-utils.js';

interface FilterOptions {
  hasText?: string | RegExp;
  hasNotText?: string | RegExp;
  hasAccessibleName?: string | RegExp;  // 新增：用于 accessible name 匹配
  exact?: boolean;
  position?: number | 'last';
}

/**
 * Locator 适配器 - 实现 Playwright Locator API
 */
class LocatorAdapter {
  private selector: string;
  private page: any; // TODO: Type this properly
  private options: LocatorOptions;
  private filters: FilterOptions[];
  private logger: Logger;
  private waitManager: any; // TODO: Type this properly
  private eventSimulator: any; // TODO: Type this properly
  private _element?: Element;
  private _parentContextLocator?: LocatorAdapter;

  constructor(selector: string, page: any, options: LocatorOptions = {}) {
    this.selector = selector;
    this.page = page;
    this.options = options;
    this.filters = [];
    this.logger = (typeof window !== 'undefined' && window.PlaywrightLogger) 
      ? new window.PlaywrightLogger() 
      : console as unknown as Logger;
    this.waitManager = page.waitManager;
    this.eventSimulator = page.eventSimulator;
  }


  // =============== 链式过滤器方法 ===============

  /**
   * 过滤 locator
   */
  filter(options: FilterOptions): LocatorAdapter {
    const newLocator = new LocatorAdapter(this.selector, this.page);
    newLocator.filters = [...this.filters, options];
    // 保持父上下文 locator 的引用
    newLocator._parentContextLocator = this._parentContextLocator;
    return newLocator;
  }

  /**
   * 获取第一个元素
   */
  first(): LocatorAdapter {
    return this.nth(0);
  }

  /**
   * 获取最后一个元素
   */
  last(): LocatorAdapter {
    return this.filter({ position: 'last' });
  }

  /**
   * 获取第 n 个元素
   */
  nth(n: number): LocatorAdapter {
    return this.filter({ position: n });
  }

  /**
   * 创建子 Locator (在当前 Locator 范围内查找)
   */
  locator(selector: string, options: LocatorOptions = {}): LocatorAdapter {
    // 创建组合选择器，表示在当前选择器范围内查找子选择器
    const combinedSelector = this.combineSelectorWithParent(selector);
    const newLocator = new LocatorAdapter(combinedSelector, this.page, options);
    // 子 locator 不继承过滤器，因为它在寻找子元素，过滤条件可能不适用
    // newLocator.filters = [...this.filters];
    return newLocator;
  }

  /**
   * 根据角色查找元素
   */
  getByRole(role: string, options: { name?: string | RegExp; exact?: boolean } = {}): LocatorAdapter {
    const { name, exact = false } = options;
    const roleOptions: RoleOptions = { exact };
    
    // 使用共享工具函数获取角色选择器
    const roleSelector = getRoleSelector(role, roleOptions);
    
    // 关键修复：只有当前 locator 有内容相关的过滤器时，才使用父上下文方式
    // 这样可以确保过滤器只应用到父元素，而不是子元素
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    let newLocator: LocatorAdapter;
    if (hasContentFilters) {
      // 有内容过滤器时，使用父上下文方式
      newLocator = new LocatorAdapter(roleSelector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      // 没有内容过滤器时，使用传统的选择器组合方式
      const combinedSelector = this.combineSelectorWithParent(roleSelector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    // 如果指定了 name，添加 accessible name 过滤
    if (name) {
      newLocator.filters.push({
        hasAccessibleName: name,
        exact
      });
    }
    
    return newLocator;
  }

  /**
   * 组合两个 XPath 表达式
   */
  private combineXPaths(parentXpath: string, childXpath: string): string {
    // 处理包含 | 操作符的复杂 XPath
    if (parentXpath.includes(' | ')) {
      // 父 XPath 有多个部分，需要为每个部分添加子路径
      const parentParts = parentXpath.split(' | ');
      const combinedParts = parentParts.map(parentPart => {
        const cleanParentPart = parentPart.trim();
        // 如果子 XPath 也有多个部分，则每个父部分都要与每个子部分组合
        if (childXpath.includes(' | ')) {
          const childParts = childXpath.split(' | ');
          return childParts.map(childPart => {
            const cleanChildPart = childPart.trim().replace(/^\/+/, '');
            return `(${cleanParentPart})//${cleanChildPart}`;
          }).join(' | ');
        } else {
          const cleanChildXpath = childXpath.replace(/^\/+/, '');
          return `(${cleanParentPart})//${cleanChildXpath}`;
        }
      });
      return `xpath=${combinedParts.join(' | ')}`;
    } else {
      // 简单情况：父 XPath 只有一个部分
      if (childXpath.includes(' | ')) {
        const childParts = childXpath.split(' | ');
        const combinedParts = childParts.map(childPart => {
          const cleanChildPart = childPart.trim().replace(/^\/+/, '');
          return `(${parentXpath})//${cleanChildPart}`;
        });
        return `xpath=${combinedParts.join(' | ')}`;
      } else {
        const cleanChildXpath = childXpath.replace(/^\/+/, '');
        return `xpath=(${parentXpath})//${cleanChildXpath}`;
      }
    }
  }

  /**
   * 将选择器与父选择器组合
   */
  private combineSelectorWithParent(childSelector: string): string {
    // 如果子选择器是 XPath，需要特殊处理
    if (childSelector.startsWith('xpath=')) {
      const childXpath = childSelector.substring(6);
      if (this.selector.startsWith('xpath=')) {
        const parentXpath = this.selector.substring(6);
        // 处理复杂的 XPath 组合，特别是包含 | 操作符的情况
        return this.combineXPaths(parentXpath, childXpath);
      } else {
        // 父选择器是 CSS，子选择器是 XPath - 转换父选择器为 XPath
        const parentXpath = this.cssSelectorToXPath(this.selector);
        return this.combineXPaths(parentXpath, childXpath);
      }
    }
    
    // 如果父选择器是 XPath，子选择器是 CSS
    if (this.selector.startsWith('xpath=')) {
      const parentXpath = this.selector.substring(6);
      const childXpath = this.cssSelectorToXPath(childSelector);
      // 使用新的 combineXPaths 方法来正确处理复杂 XPath
      return this.combineXPaths(parentXpath, childXpath);
    }
    
    // 两个都是 CSS 选择器
    // 处理包含逗号的复杂选择器
    if (this.selector.includes(',')) {
      const parentParts = this.selector.split(',').map(part => part.trim());
      const combinedParts = parentParts.map(parentPart => `${parentPart} ${childSelector}`);
      return combinedParts.join(', ');
    } else {
      return `${this.selector} ${childSelector}`;
    }
  }

  /**
   * 将 CSS 选择器转换为 XPath 表达式（改进版）
   */
  private cssSelectorToXPath(cssSelector: string): string {
    // 处理逗号分隔的多个选择器
    if (cssSelector.includes(',')) {
      const selectors = cssSelector.split(',').map(s => s.trim());
      const xpathParts = selectors.map(sel => this.singleCssToXPath(sel));
      return xpathParts.join(' | ');
    }
    
    return this.singleCssToXPath(cssSelector);
  }

  /**
   * 将单个 CSS 选择器转换为 XPath 表达式
   */
  private singleCssToXPath(cssSelector: string): string {
    const trimmed = cssSelector.trim();
    
    if (trimmed.startsWith('#')) {
      // ID 选择器: #id -> //*[@id="id"]
      return `//*[@id="${trimmed.substring(1)}"]`;
    } else if (trimmed.startsWith('.')) {
      // 类选择器: .class -> //*[contains(@class, "class")]
      return `//*[contains(@class, "${trimmed.substring(1)}")]`;
    } else if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      // 属性选择器
      const attrMatch = trimmed.match(/\[([^=]+)="([^"]+)"\]/);
      if (attrMatch) {
        return `//*[@${attrMatch[1]}="${attrMatch[2]}"]`;
      }
      const attrExistsMatch = trimmed.match(/\[([^=\]]+)\]/);
      if (attrExistsMatch) {
        return `//*[@${attrExistsMatch[1]}]`;
      }
    } else if (/^[a-zA-Z][a-zA-Z0-9-]*$/.test(trimmed)) {
      // 标签选择器: div -> //div
      return `//${trimmed}`;
    } else if (trimmed === '*') {
      // 通配符选择器: * -> //*
      return `//*`;
    } else if (trimmed.startsWith('*[') && trimmed.endsWith(']')) {
      // 通配符属性选择器: *[attr="value"] -> //*[@attr="value"]
      const attrPart = trimmed.substring(2, trimmed.length - 1);
      const attrMatch = attrPart.match(/([^=]+)="([^"]+)"/);
      if (attrMatch) {
        return `//*[@${attrMatch[1]}="${attrMatch[2]}"]`;
      }
      const attrExistsMatch = attrPart.match(/^([^=\]]+)$/);
      if (attrExistsMatch) {
        return `//*[@${attrExistsMatch[1]}]`;
      }
    }
    
    // 复杂选择器 - 回退到通配符，但提供更好的处理
    // 尝试提取标签名
    const tagMatch = trimmed.match(/^([a-zA-Z][a-zA-Z0-9-]*)/);
    if (tagMatch) {
      return `//${tagMatch[1]}`;
    }
    
    // 最后的回退 - 使用通配符
    return `//*`;
  }

  /**
   * 根据文本过滤
   */
  getByText(text: string, options: { exact?: boolean } = {}): LocatorAdapter {
    const { exact = false } = options;
    const selector = buildGetByTextSelector(text, exact);
    
    // getByText 检查是否有内容过滤器
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    let newLocator: LocatorAdapter;
    if (hasContentFilters) {
      newLocator = new LocatorAdapter(selector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      const combinedSelector = this.combineSelectorWithParent(selector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    return newLocator;
  }

  /**
   * 根据标签定位
   */
  getByLabel(text: string, options: { exact?: boolean } = {}): LocatorAdapter {
    const { exact = false } = options;
    
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    // 如果是空字符串，直接使用过滤器匹配没有 label 的元素
    if (text === "") {
      const formSelector = 'input, select, textarea';
      let newLocator: LocatorAdapter;
      
      if (hasContentFilters) {
        newLocator = new LocatorAdapter(formSelector, this.page);
        newLocator._parentContextLocator = this;
      } else {
        const combinedSelector = this.combineSelectorWithParent(formSelector);
        newLocator = new LocatorAdapter(combinedSelector, this.page);
      }
      
      // 添加过滤器：匹配没有任何 label 的元素
      newLocator.filters.push({
        hasAccessibleName: "",
        exact: true
      });
      
      return newLocator;
    }
    
    // 使用共享的选择器生成器
    const selector = buildGetByLabelSelector(text, exact);
    let newLocator: LocatorAdapter;
    
    if (hasContentFilters) {
      newLocator = new LocatorAdapter(selector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      const combinedSelector = this.combineSelectorWithParent(selector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    return newLocator;
  }

  /**
   * 根据占位符定位
   */
  getByPlaceholder(text: string, options: { exact?: boolean } = {}): LocatorAdapter {
    const { exact = false } = options;
    const selector = buildGetByPlaceholderSelector(text, exact);
    
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    let newLocator: LocatorAdapter;
    if (hasContentFilters) {
      newLocator = new LocatorAdapter(selector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      const combinedSelector = this.combineSelectorWithParent(selector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    return newLocator;
  }

  /**
   * 根据测试 ID 定位
   */
  getByTestId(testId: string): LocatorAdapter {
    const selector = buildGetByTestIdSelector(testId);
    
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    let newLocator: LocatorAdapter;
    if (hasContentFilters) {
      newLocator = new LocatorAdapter(selector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      const combinedSelector = this.combineSelectorWithParent(selector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    return newLocator;
  }

  /**
   * 根据标题定位
   */
  getByTitle(text: string, options: { exact?: boolean } = {}): LocatorAdapter {
    const { exact = false } = options;
    const selector = buildGetByTitleSelector(text, exact);
    
    const hasContentFilters = this.filters.some(filter => 
      filter.hasText !== undefined || filter.hasNotText !== undefined
    );
    
    let newLocator: LocatorAdapter;
    if (hasContentFilters) {
      newLocator = new LocatorAdapter(selector, this.page);
      newLocator._parentContextLocator = this;
    } else {
      const combinedSelector = this.combineSelectorWithParent(selector);
      newLocator = new LocatorAdapter(combinedSelector, this.page);
    }
    
    return newLocator;
  }

  // =============== 原生事件触发辅助方法 ===============
  
  /**
   * 触发原生输入事件
   */
  private triggerNativeInputEvents(element: HTMLInputElement | HTMLTextAreaElement, value: string): void {
    // 触发 input 事件
    const inputEvent = new Event('input', { bubbles: true, cancelable: true });
    Object.defineProperty(inputEvent, 'target', { value: element, enumerable: true });
    element.dispatchEvent(inputEvent);
    
    // 触发 change 事件
    const changeEvent = new Event('change', { bubbles: true, cancelable: true });
    Object.defineProperty(changeEvent, 'target', { value: element, enumerable: true });
    element.dispatchEvent(changeEvent);
    
    // 触发用户交互事件
    this.triggerNativeInteractionEvents(element);
  }
  
  /**
   * 触发原生 change 事件
   */
  private triggerNativeChangeEvent(element: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement): void {
    const changeEvent = new Event('change', { bubbles: true, cancelable: true });
    Object.defineProperty(changeEvent, 'target', { value: element, enumerable: true });
    element.dispatchEvent(changeEvent);
  }
  
  /**
   * 触发原生用户交互事件
   */
  private triggerNativeInteractionEvents(element: Element): void {
    try {
      element.dispatchEvent(new Event('focus', { bubbles: true }));
      setTimeout(() => {
        element.dispatchEvent(new Event('blur', { bubbles: true }));
      }, 10);
    } catch (error) {
      // 忽略交互事件错误
    }
  }

  // =============== 核心操作方法 ===============

  /**
   * 点击元素
   */
  async click(options: ClickOptions = {}): Promise<void> {
    const element = await this.getElement();
    await this.page.scrollIntoViewIfNeeded(element);
    
    // 检查框架组件类型并使用相应适配器
    const reactAdapter = getReactAdapter(this.logger);
    const openinulaAdapter = getOpenInulaAdapter(this.logger);
    
    const isReactComponent = reactAdapter.isReactComponent(element);
    const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
    
    if (isReactComponent) {
      // React 组件：使用 React 适配器
      const clickResult = await reactAdapter.triggerClickEvent(element);
      this.logger.debug(`点击元素完成: ${this.selector} (${clickResult.method})`);
    } else if (isOpenInulaComponent) {
      // OpenInula 组件：使用 OpenInula 适配器
      const clickResult = await openinulaAdapter.triggerClickEvent(element);
      this.logger.debug(`点击元素完成: ${this.selector} (${clickResult.method})`);
    } else {
      // 原生元素：使用原生事件模拟器
      this.eventSimulator.simulateClick(element, options);
      this.logger.debug(`点击元素: ${this.selector} (native)`);
    }
  }

  /**
   * 双击元素
   */
  async dblclick(options: ClickOptions = {}): Promise<void> {
    const element = await this.getElement();
    await this.page.scrollIntoViewIfNeeded(element);
    
    // 检查框架组件类型并使用相应适配器
    const reactAdapter = getReactAdapter(this.logger);
    const openinulaAdapter = getOpenInulaAdapter(this.logger);
    
    const isReactComponent = reactAdapter.isReactComponent(element);
    const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
    
    if (isReactComponent || isOpenInulaComponent) {
      // 对于框架组件，双击就是触发两次点击事件
      if (isReactComponent) {
        await reactAdapter.triggerClickEvent(element);
        await reactAdapter.triggerClickEvent(element);
        this.logger.debug(`双击元素完成: ${this.selector} (react)`);
      } else {
        await openinulaAdapter.triggerClickEvent(element);
        await openinulaAdapter.triggerClickEvent(element);
        this.logger.debug(`双击元素完成: ${this.selector} (openinula)`);
      }
    } else {
      // 原生元素：使用原生事件模拟器
      this.eventSimulator.simulateDoubleClick(element);
      this.logger.debug(`双击元素: ${this.selector} (native)`);
    }
  }

  /**
   * 填充表单
   */
  async fill(value: string, options: FillOptions = {}): Promise<void> {
    const element = await this.getElement() as HTMLInputElement | HTMLTextAreaElement;
    await this.page.scrollIntoViewIfNeeded(element);
    
    // 清空并填充
    element.value = '';
    element.value = value;
    
    // 检查框架组件类型并使用相应适配器
    const reactAdapter = getReactAdapter(this.logger);
    const openinulaAdapter = getOpenInulaAdapter(this.logger);
    
    const isReactComponent = reactAdapter.isReactComponent(element);
    const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
    
    if (isReactComponent) {
      // React 组件：使用 React 适配器
      await reactAdapter.triggerInputEvent(element, value);
      const changeResult = await reactAdapter.triggerChangeEvent(element, value);
      await reactAdapter.triggerInteractionEvents(element);
      
      this.logger.debug(`填充元素完成: ${this.selector} = "${value}" (${changeResult.method})`);
    } else if (isOpenInulaComponent) {
      // OpenInula 组件：使用 OpenInula 适配器
      await openinulaAdapter.triggerInputEvent(element, value);
      const changeResult = await openinulaAdapter.triggerChangeEvent(element, value);
      await openinulaAdapter.triggerInteractionEvents(element);
      
      this.logger.debug(`填充元素完成: ${this.selector} = "${value}" (${changeResult.method})`);
    } else {
      // 原生元素：直接触发原生事件
      this.triggerNativeInputEvents(element, value);
      this.logger.debug(`填充元素完成: ${this.selector} = "${value}" (native)`);
    }
  }

  /**
   * 按键操作
   */
  async press(key: string, options: TypeOptions = {}): Promise<void> {
    const element = await this.getElement() as HTMLElement;
    element.focus();
    
    this.eventSimulator.simulateKeyPress(element, key, options);
    this.logger.debug(`按键: ${this.selector} -> ${key}`);
  }

  /**
   * 逐字符输入（模拟打字）
   */
  async pressSequentially(text: string, options: TypeOptions = {}): Promise<void> {
    const element = await this.getElement() as HTMLInputElement | HTMLTextAreaElement;
    await this.eventSimulator.simulateTyping(element, text, options);
    this.logger.debug(`逐字符输入: ${this.selector} -> "${text}"`);
  }

  /**
   * 悬停
   */
  async hover(): Promise<void> {
    const element = await this.getElement() as HTMLElement;
    await this.page.scrollIntoViewIfNeeded(element);
    
    // 检查框架组件类型并触发相应事件
    const reactAdapter = getReactAdapter(this.logger);
    const openinulaAdapter = getOpenInulaAdapter(this.logger);
    
    const isReactComponent = reactAdapter.isReactComponent(element);
    const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
    
    if (isReactComponent || isOpenInulaComponent) {
      // 对于框架组件，触发 mouseenter 和 mouseover 事件
      element.dispatchEvent(new Event('mouseenter', { bubbles: true }));
      element.dispatchEvent(new Event('mouseover', { bubbles: true }));
      this.logger.debug(`悬停元素完成: ${this.selector} (${isReactComponent ? 'react' : 'openinula'})`);
    } else {
      // 原生元素：使用原生事件模拟器
      this.eventSimulator.simulateHover(element);
      this.logger.debug(`悬停元素: ${this.selector} (native)`);
    }
  }

  /**
   * 选择复选框
   */
  async check(): Promise<void> {
    const element = await this.getElement() as HTMLInputElement;
    if (element.type === 'checkbox' || element.type === 'radio') {
      element.checked = true;
      
      // 检查框架组件类型并使用相应适配器
      const reactAdapter = getReactAdapter(this.logger);
      const openinulaAdapter = getOpenInulaAdapter(this.logger);
      
      const isReactComponent = reactAdapter.isReactComponent(element);
      const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
      
      if (isReactComponent) {
        const changeResult = await reactAdapter.triggerChangeEvent(element);
        this.logger.debug(`选择复选框: ${this.selector} (${changeResult.method})`);
      } else if (isOpenInulaComponent) {
        const changeResult = await openinulaAdapter.triggerChangeEvent(element);
        this.logger.debug(`选择复选框: ${this.selector} (${changeResult.method})`);
      } else {
        this.triggerNativeChangeEvent(element);
        this.logger.debug(`选择复选框: ${this.selector} (native)`);
      }
    }
  }

  /**
   * 取消选择复选框
   */
  async uncheck(): Promise<void> {
    const element = await this.getElement() as HTMLInputElement;
    if (element.type === 'checkbox') {
      element.checked = false;
      
      // 检查框架组件类型并使用相应适配器
      const reactAdapter = getReactAdapter(this.logger);
      const openinulaAdapter = getOpenInulaAdapter(this.logger);
      
      const isReactComponent = reactAdapter.isReactComponent(element);
      const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
      
      if (isReactComponent) {
        const changeResult = await reactAdapter.triggerChangeEvent(element);
        this.logger.debug(`取消选择复选框: ${this.selector} (${changeResult.method})`);
      } else if (isOpenInulaComponent) {
        const changeResult = await openinulaAdapter.triggerChangeEvent(element);
        this.logger.debug(`取消选择复选框: ${this.selector} (${changeResult.method})`);
      } else {
        this.triggerNativeChangeEvent(element);
        this.logger.debug(`取消选择复选框: ${this.selector} (native)`);
      }
    }
  }

  /**
   * 选择下拉选项
   */
  async selectOption(values: string | string[]): Promise<void> {
    const element = await this.getElement() as HTMLSelectElement;
    if (element.tagName === 'SELECT') {
      if (Array.isArray(values)) {
        // 多选
        Array.from(element.options).forEach(option => {
          option.selected = values.includes(option.value) || values.includes(option.text);
        });
      } else {
        element.value = values;
      }
      
      // 检查框架组件类型并使用相应适配器
      const reactAdapter = getReactAdapter(this.logger);
      const openinulaAdapter = getOpenInulaAdapter(this.logger);
      
      const isReactComponent = reactAdapter.isReactComponent(element);
      const isOpenInulaComponent = openinulaAdapter.isOpenInulaComponent(element);
      
      if (isReactComponent) {
        const changeResult = await reactAdapter.triggerChangeEvent(element);
        this.logger.debug(`选择下拉选项: ${this.selector} = ${values} (${changeResult.method})`);
      } else if (isOpenInulaComponent) {
        const changeResult = await openinulaAdapter.triggerChangeEvent(element);
        this.logger.debug(`选择下拉选项: ${this.selector} = ${values} (${changeResult.method})`);
      } else {
        this.triggerNativeChangeEvent(element);
        this.logger.debug(`选择下拉选项: ${this.selector} = ${values} (native)`);
      }
    }
  }

  // =============== 状态检查方法 ===============

  /**
   * 检查元素是否可见
   */
  async isVisible(): Promise<boolean> {
    try {
      const element = await this.getElement();
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && 
             style.visibility !== 'hidden' && style.display !== 'none' &&
             (element as HTMLElement).offsetParent !== null;
    } catch (error) {
      return false;
    }
  }

  /**
   * 检查元素是否隐藏
   */
  async isHidden(): Promise<boolean> {
    return !(await this.isVisible());
  }

  /**
   * 检查元素是否启用
   */
  async isEnabled(): Promise<boolean> {
    try {
      const element = await this.getElement() as HTMLInputElement | HTMLButtonElement | HTMLSelectElement | HTMLTextAreaElement;
      return !element.disabled && !element.hasAttribute('disabled');
    } catch (error) {
      return false;
    }
  }

  /**
   * 检查元素是否禁用
   */
  async isDisabled(): Promise<boolean> {
    return !(await this.isEnabled());
  }

  /**
   * 检查复选框是否选中
   */
  async isChecked(): Promise<boolean> {
    try {
      const element = await this.getElement() as HTMLInputElement;
      return element.checked || false;
    } catch (error) {
      return false;
    }
  }

  // =============== 内容获取方法 ===============

  /**
   * 获取文本内容
   */
  async textContent(): Promise<string> {
    const element = await this.getElement();
    return element.textContent || '';
  }

  /**
   * 获取内部文本
   */
  async innerText(): Promise<string> {
    const element = await this.getElement() as HTMLElement;
    return element.innerText || '';
  }

  /**
   * 获取 HTML 内容
   */
  async innerHTML(): Promise<string> {
    const element = await this.getElement() as HTMLElement;
    return element.innerHTML || '';
  }

  /**
   * 获取属性值
   */
  async getAttribute(name: string): Promise<string | null> {
    const element = await this.getElement();
    return element.getAttribute(name);
  }

  /**
   * 获取输入值
   */
  async inputValue(): Promise<string> {
    const element = await this.getElement() as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
    return element.value || '';
  }

  // =============== 等待方法 ===============

  /**
   * 等待元素状态
   */
  async waitFor(options: ElementWaitOptions = {}): Promise<void> {
    const { state = 'visible', timeout = 30000 } = options;
    
    switch (state) {
      case 'visible':
        return this.waitForVisible(timeout);
      case 'hidden':
        return this.waitForHidden(timeout);
      case 'attached':
        return this.waitForAttached(timeout);
      case 'detached':
        return this.waitForDetached(timeout);
      default:
        throw new Error(`未知的等待状态: ${state}`);
    }
  }

  /**
   * 等待可见
   */
  private async waitForVisible(timeout: number): Promise<void> {
    return this.waitManager.waitForCondition(
      () => this.isVisible(),
      timeout,
      `元素 "${this.selector}" 等待可见超时`
    );
  }

  /**
   * 等待隐藏
   */
  private async waitForHidden(timeout: number): Promise<void> {
    return this.waitManager.waitForCondition(
      () => this.isHidden(),
      timeout,
      `元素 "${this.selector}" 等待隐藏超时`
    );
  }

  /**
   * 等待附加到DOM
   */
  private async waitForAttached(timeout: number): Promise<void> {
    return this.waitManager.waitForCondition(
      async () => (await this.count()) > 0,
      timeout,
      `元素 "${this.selector}" 等待附加到DOM超时`
    );
  }

  /**
   * 等待从DOM分离
   */
  private async waitForDetached(timeout: number): Promise<void> {
    return this.waitManager.waitForCondition(
      async () => (await this.count()) === 0,
      timeout,
      `元素 "${this.selector}" 等待从DOM分离超时`
    );
  }

  // =============== 查询方法 ===============

  /**
   * 查询所有匹配的元素
   */
  private queryElements(selector: string): Element[] {
    // 如果有父上下文 locator，在父上下文中查找
    if (this._parentContextLocator) {
      const parentElements = this._parentContextLocator.queryElements(this._parentContextLocator.selector);
      const filteredParentElements = this._parentContextLocator.applyFilters(parentElements);
      
      const allResults: Element[] = [];
      
      // 在每个过滤后的父元素中查找子元素
      for (const parentElement of filteredParentElements) {
        let childElements: Element[] = [];
        
        if (selector.startsWith('xpath=')) {
          const xpath = selector.substring(6);
          const result = document.evaluate(xpath, parentElement, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
          for (let i = 0; i < result.snapshotLength; i++) {
            const element = result.snapshotItem(i);
            if (element) childElements.push(element as Element);
          }
        } else {
          childElements = Array.from(parentElement.querySelectorAll(selector));
        }
        
        allResults.push(...childElements);
      }
      
      return allResults;
    }
    
    // 正常的全局查询
    if (selector.startsWith('xpath=')) {
      const xpath = selector.substring(6);
      const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      const elements: Element[] = [];
      for (let i = 0; i < result.snapshotLength; i++) {
        const element = result.snapshotItem(i);
        if (element) elements.push(element as Element);
      }
      return elements;
    } else {
      return Array.from(document.querySelectorAll(selector));
    }
  }

  /**
   * 获取匹配元素的数量
   */
  async count(): Promise<number> {
    const elements = this.queryElements(this.selector);
    return this.applyFilters(elements).length;
  }

  /**
   * 获取所有匹配的 locator
   */
  async all(): Promise<LocatorAdapter[]> {
    const elements = this.queryElements(this.selector);
    const filteredElements = this.applyFilters(elements);
    
    return filteredElements.map(element => {
      const locator = new LocatorAdapter(this.buildUniqueSelector(element), this.page);
      locator._element = element;
      return locator;
    });
  }

  /**
   * 获取单个元素
   */
  async getElement(): Promise<Element> {
    if (this._element && document.contains(this._element)) {
      return this._element;
    }

    const elements = this.queryElements(this.selector);
    if (elements.length === 0) {
      throw new Error(`找不到元素: ${this.selector}`);
    }

    const filteredElements = this.applyFilters(elements);
    if (filteredElements.length === 0) {
      throw new Error(`过滤后找不到元素: ${this.selector}`);
    }

    return filteredElements[0];
  }

  /**
   * 应用过滤器
   */
  private applyFilters(elements: Element[]): Element[] {
    let filtered = elements;
    
    for (const filter of this.filters) {
      filtered = this.applyFilter(filtered, filter);
    }
    
    return filtered;
  }

  /**
   * 应用单个过滤器
   */
  private applyFilter(elements: Element[], filter: FilterOptions): Element[] {
    if (typeof filter.position === 'number') {
      return elements[filter.position] ? [elements[filter.position]] : [];
    }
    
    if (filter.position === 'last') {
      return elements.length > 0 ? [elements[elements.length - 1]] : [];
    }
    
    if (filter.hasText) {
      return elements.filter(element => {
        // filter.hasText 只匹配元素的文本内容，不匹配 accessible name 相关属性
        return elementMatchesText(element, filter.hasText!, filter.exact);
      });
    }
    
    if (filter.hasAccessibleName) {
      return elements.filter(element => {
        // filter.hasAccessibleName 匹配完整的 accessible name
        return elementMatchesAccessibleName(element, filter.hasAccessibleName!, filter.exact);
      });
    }
    
    if (filter.hasNotText) {
      return elements.filter(element => {
        const text = element.textContent || (element as HTMLElement).innerText || '';
        if (filter.hasNotText instanceof RegExp) {
          return !filter.hasNotText.test(text);
        }
        return !text.includes(filter.hasNotText as string);
      });
    }
    
    return elements;
  }

  /**
   * 构建唯一选择器
   */
  private buildUniqueSelector(element: Element): string {
    if (element.id) {
      return `#${element.id}`;
    }
    
    const path: string[] = [];
    let current: Element | null = element;
    
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      
      if (current.className) {
        const classes = current.className.split(' ').filter(cls => cls.trim());
        if (classes.length > 0) {
          selector += '.' + classes.join('.');
        }
      }
      
      const siblings = Array.from(current.parentNode?.children || []).filter(
        child => child.tagName === current!.tagName
      );
      
      if (siblings.length > 1) {
        const index = siblings.indexOf(current);
        selector += `:nth-of-type(${index + 1})`;
      }
      
      path.unshift(selector);
      current = current.parentElement;
    }
    
    return path.join(' > ');
  }
}


// 导出给浏览器使用
if (typeof window !== 'undefined') {
  window.PlaywrightLocatorAdapter = LocatorAdapter;
}


// ES6 模块导出
export default LocatorAdapter;