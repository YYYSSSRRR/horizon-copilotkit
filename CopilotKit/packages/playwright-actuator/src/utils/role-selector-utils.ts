/**
 * 角色选择器工具 - 提供统一的角色到选择器映射逻辑
 */

export interface RoleOptions {
  name?: string | RegExp;
  exact?: boolean;
  level?: number;
}

/**
 * 角色到选择器的映射表
 * 包含显式 role 属性和隐式角色元素
 */
export const ROLE_SELECTORS: Record<string, string> = {
  'button': 'button, input[type="button"], input[type="submit"], input[type="reset"], [role="button"]',
  'link': 'a[href], [role="link"]',
  'textbox': 'input:not([type]), input[type=""], input[type="text"], input[type="email"], input[type="password"], input[type="search"], input[type="tel"], input[type="url"], input[type="date"], textarea, [role="textbox"]',
  'combobox': 'select, [role="combobox"]',
  'checkbox': 'input[type="checkbox"], [role="checkbox"]',
  'radio': 'input[type="radio"], [role="radio"]',
  'spinbutton': 'input[type="number"], [role="spinbutton"]',
  'slider': 'input[type="range"], [role="slider"]',
  'searchbox': 'input[type="search"], [role="searchbox"]',
  'heading': 'h1, h2, h3, h4, h5, h6, [role="heading"]',
  'img': 'img, [role="img"]',
  'list': 'ul, ol, [role="list"]',
  'listitem': 'li, [role="listitem"]',
  'listbox': 'select[multiple], [role="listbox"]',
  'option': 'option, [role="option"]',
  'tab': '[role="tab"]',
  'tabpanel': '[role="tabpanel"]',
  'dialog': '[role="dialog"], dialog',
  'table': 'table, [role="table"]',
  'row': 'tr, [role="row"]',
  'cell': 'td, [role="cell"]',
  'columnheader': 'th, [role="columnheader"]',
  'rowheader': 'th[scope="row"], [role="rowheader"]'
};

/**
 * 获取角色对应的 CSS 选择器
 */
export function getRoleSelector(role: string, options: RoleOptions = {}): string {
  const { level } = options;
  
  // 处理带级别的标题角色
  if (level && role === 'heading') {
    return `h${level}[role="heading"], h${level}`;
  }
  
  // 返回预定义的角色选择器，如果没有则回退到基本 role 属性
  return ROLE_SELECTORS[role] || `[role="${role}"]`;
}

/**
 * 构建带名称匹配的 XPath 表达式
 * 支持所有 accessible name 的来源方式
 */
export function buildRoleXPathWithName(role: string, name: string, options: RoleOptions = {}): string {
  const { exact = false } = options;
  const selector = getRoleSelector(role, options);
  
  // 将 CSS 选择器转换为 XPath 部分
  const xpathParts: string[] = [];
  const selectorParts = selector.split(', ');
  
  selectorParts.forEach(part => {
    const trimmedPart = part.trim();
    let xpathPart = '';
    
    // 特殊处理复杂的 CSS 选择器
    if (trimmedPart === 'input:not([type])') {
      xpathPart = '//input[not(@type)]';
    } else if (trimmedPart === 'input[type=""]') {
      xpathPart = '//input[@type=""]';
    } else if (trimmedPart.includes('[')) {
      // 处理带属性的元素，如 input[type="text"]
      const [tag, attrPart] = trimmedPart.split('[');
      const attr = attrPart.replace(/\]$/, '');
      
      if (attr.includes('=')) {
        // 有值的属性，如 type="button"
        const [attrName, attrValue] = attr.split('=');
        const cleanAttrName = attrName.trim();
        const cleanAttrValue = attrValue.replace(/['"]/g, '').trim();
        xpathPart = `//${tag}[@${cleanAttrName}="${cleanAttrValue}"]`;
      } else {
        // 仅存在性检查的属性
        const cleanAttrName = attr.trim();
        xpathPart = `//${tag}[@${cleanAttrName}]`;
      }
    } else {
      // 简单标签名
      xpathPart = `//${trimmedPart}`;
    }
    
    // 构建 accessible name 匹配条件（按优先级排序）
    const nameConditions: string[] = [];
    
    if (exact) {
      // 1. aria-label（最高优先级）
      nameConditions.push(`@aria-label="${name}"`);
      // 2. aria-labelledby 引用的元素文本
      nameConditions.push(`@aria-labelledby = //label[normalize-space(text())="${name}"]/@id`);
      nameConditions.push(`@aria-labelledby = //*[normalize-space(text())="${name}"]/@id`);
      // 3. for 关联的 label 文本
      nameConditions.push(`@id = //label[normalize-space(text())="${name}"]/@for`);
      // 4. 父级 label 的文本内容
      nameConditions.push(`parent::label[normalize-space(text())="${name}"]`);
      nameConditions.push(`ancestor::label[normalize-space(text())="${name}"]`);
      // 5. 元素自身的文本内容
      nameConditions.push(`normalize-space(text())="${name}"`);
      // 6. placeholder 作为 fallback
      nameConditions.push(`@placeholder="${name}"`);
      // 7. title 作为 fallback
      nameConditions.push(`@title="${name}"`);
    } else {
      // 包含匹配
      nameConditions.push(`contains(@aria-label, "${name}")`);
      nameConditions.push(`@aria-labelledby = //label[contains(normalize-space(text()), "${name}")]/@id`);
      nameConditions.push(`@aria-labelledby = //*[contains(normalize-space(text()), "${name}")]/@id`);
      nameConditions.push(`@id = //label[contains(normalize-space(text()), "${name}")]/@for`);
      nameConditions.push(`parent::label[contains(normalize-space(text()), "${name}")]`);
      nameConditions.push(`ancestor::label[contains(normalize-space(text()), "${name}")]`);
      nameConditions.push(`contains(normalize-space(text()), "${name}")`);
      nameConditions.push(`contains(@placeholder, "${name}")`);
      nameConditions.push(`contains(@title, "${name}")`);
    }
    
    // 组合所有条件
    const combinedCondition = nameConditions.join(' or ');
    xpathParts.push(`${xpathPart}[${combinedCondition}]`);
  });
  
  return xpathParts.join(' | ');
}

/**
 * 检查元素是否匹配指定名称
 * 按照 accessible name 的优先级顺序检查
 */
export function elementMatchesName(element: Element, name: string | RegExp, exact: boolean = false): boolean {
  
  // 1. 优先检查 aria-label
  const ariaLabel = element.getAttribute('aria-label') || '';
  if (ariaLabel && matchesText(ariaLabel, name, exact)) {
    return true;
  }
  
  // 2. 检查 aria-labelledby 引用的元素
  const ariaLabelledBy = element.getAttribute('aria-labelledby');
  if (ariaLabelledBy) {
    const labelElement = document.getElementById(ariaLabelledBy);
    if (labelElement) {
      const labelText = labelElement.textContent?.trim() || '';
      if (matchesText(labelText, name, exact)) {
        return true;
      }
    }
  }
  
  // 3. 检查关联的 label（通过 for 属性）
  const elementId = element.getAttribute('id');
  if (elementId) {
    const labelElement = document.querySelector(`label[for="${elementId}"]`);
    if (labelElement) {
      const labelText = labelElement.textContent?.trim() || '';
      if (matchesText(labelText, name, exact)) {
        return true;
      }
    }
  }
  
  // 4. 检查父级或祖先 label 元素
  let parent = element.parentElement;
  while (parent) {
    if (parent.tagName.toLowerCase() === 'label') {
      const labelText = parent.textContent?.trim() || '';
      if (matchesText(labelText, name, exact)) {
        return true;
      }
      break; // 找到第一个 label 祖先就停止
    }
    parent = parent.parentElement;
  }
  
  // 5. 检查元素自身的文本内容
  const textContent = element.textContent?.trim() || '';
  if (matchesText(textContent, name, exact)) {
    return true;
  }
  
  // 6. 检查 placeholder 属性（fallback）
  const placeholder = element.getAttribute('placeholder') || '';
  if (matchesText(placeholder, name, exact)) {
    return true;
  }
  
  // 7. 检查 title 属性（fallback）
  const title = element.getAttribute('title') || '';
  if (matchesText(title, name, exact)) {
    return true;
  }
  
  return false;
}

/**
 * 文本匹配辅助函数
 */
function matchesText(text: string, pattern: string | RegExp, exact: boolean): boolean {
  if (pattern instanceof RegExp) {
    return pattern.test(text);
  }
  
  if (exact) {
    return text === pattern;
  }
  
  return text.includes(pattern);
}