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
    
    if (trimmedPart.includes('[')) {
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
    
    // 添加名称匹配条件
    if (exact) {
      xpathParts.push(`${xpathPart}[@aria-label="${name}"] | ${xpathPart}[normalize-space(text())="${name}"]`);
    } else {
      xpathParts.push(`${xpathPart}[contains(@aria-label, "${name}")] | ${xpathPart}[contains(normalize-space(text()), "${name}")]`);
    }
  });
  
  return xpathParts.join(' | ');
}

/**
 * 检查元素是否匹配指定名称
 */
export function elementMatchesName(element: Element, name: string | RegExp, exact: boolean = false): boolean {
  const ariaLabel = element.getAttribute('aria-label') || '';
  const textContent = element.textContent?.trim() || '';
  
  if (name instanceof RegExp) {
    return name.test(ariaLabel) || name.test(textContent);
  }
  
  if (exact) {
    return ariaLabel === name || textContent === name;
  }
  
  return ariaLabel.includes(name) || textContent.includes(name);
}