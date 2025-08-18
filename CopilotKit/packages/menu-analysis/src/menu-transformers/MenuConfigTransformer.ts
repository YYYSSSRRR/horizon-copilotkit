import { MenuItem } from '../types';

/**
 * 原始菜单配置项接口（从menus-config.json）
 */
export interface RawMenuConfig {
  [key: string]: RawMenuItem;
}

export interface RawMenuItem {
  name?: string;
  abbr?: string;
  order?: number;
  preferNewWindow?: boolean;
  test?: string;
  tags?: Record<string, boolean>;
  emit?: string[];
  href?: string;
  isearch?: string;
  icon?: {
    url: string;
  };
  subs?: Record<string, RawMenuItem>;
  actions?: Record<string, RawMenuItem>;
}

/**
 * 菜单配置转换器
 */
export class MenuConfigTransformer {
  
  /**
   * 将原始菜单配置转换为MenuItem数组
   */
  static transformToMenuItems(rawConfig: RawMenuConfig): MenuItem[] {
    const menuItems: MenuItem[] = [];
    
    this.processMenuLevel(rawConfig, menuItems, 0);
    
    return menuItems;
  }
  
  /**
   * 递归处理菜单层级
   */
  private static processMenuLevel(
    menuLevel: Record<string, RawMenuItem>, 
    menuItems: MenuItem[], 
    level: number,
    parentId?: string
  ): void {
    
    Object.keys(menuLevel).forEach(key => {
      const rawItem = menuLevel[key];
      
      // 生成菜单ID（使用key转换为kebab-case）
      const id = this.generateMenuId(key);
      
      // 创建MenuItem
      const menuItem: MenuItem = {
        id,
        text: rawItem.name || key,
        level,
        parentId,
        hasSubmenu: !!(rawItem.subs || rawItem.actions),
        emit: rawItem.emit || []
      };
      
      // 如果有href，添加到emit中
      if (rawItem.href) {
        if (!menuItem.emit?.length) {
          menuItem.emit = ['jumpSPAPage', `{'Href': '${rawItem.href}'}`];
        }
      }
      
      // 如果有emit但格式不完整，补充jumpSPAPage
      if (menuItem.emit?.length === 1 && !menuItem.emit[0].includes('jump')) {
        menuItem.emit = ['jumpSPAPage', menuItem.emit[0]];
      }
      
      menuItems.push(menuItem);
      
      // 递归处理子菜单
      if (rawItem.subs) {
        this.processMenuLevel(rawItem.subs, menuItems, level + 1, id);
      }
      
      if (rawItem.actions) {
        this.processMenuLevel(rawItem.actions, menuItems, level + 1, id);
      }
    });
  }
  
  /**
   * 生成菜单ID（转换为kebab-case）
   */
  private static generateMenuId(key: string): string {
    return key
      .replace(/([A-Z])/g, '-$1')
      .toLowerCase()
      .replace(/^-/, '')
      .replace(/_/g, '-');
  }
  
  /**
   * 从文件路径加载并转换菜单配置
   */
  static async transformFromFile(filePath: string): Promise<MenuItem[]> {
    try {
      const fs = await import('fs');
      const path = await import('path');
      
      const absolutePath = path.resolve(filePath);
      const rawData = fs.readFileSync(absolutePath, 'utf-8');
      const rawConfig: RawMenuConfig = JSON.parse(rawData);
      
      return this.transformToMenuItems(rawConfig);
      
    } catch (error) {
      throw new Error(`Failed to transform menu config from file: ${error}`);
    }
  }
  
  /**
   * 根据父菜单ID过滤菜单项
   */
  static filterByParent(menuItems: MenuItem[], parentId?: string): MenuItem[] {
    return menuItems.filter(item => item.parentId === parentId);
  }
  
  /**
   * 获取顶级菜单项
   */
  static getTopLevelMenus(menuItems: MenuItem[]): MenuItem[] {
    return this.filterByParent(menuItems, undefined);
  }
  
  /**
   * 根据ID查找菜单项
   */
  static findById(menuItems: MenuItem[], id: string): MenuItem | undefined {
    return menuItems.find(item => item.id === id);
  }
  
  /**
   * 获取菜单项的所有子菜单
   */
  static getChildren(menuItems: MenuItem[], parentId: string): MenuItem[] {
    return this.filterByParent(menuItems, parentId);
  }
  
  /**
   * 构建菜单项的完整路径
   */
  static getMenuPath(menuItems: MenuItem[], menuId: string): string[] {
    const path: string[] = [];
    let currentId = menuId;
    
    while (currentId) {
      const item = this.findById(menuItems, currentId);
      if (!item) break;
      
      path.unshift(item.text);
      currentId = item.parentId || '';
    }
    
    return path;
  }
  
  /**
   * 将MenuItem数组转换为树形结构（用于调试和展示）
   */
  static toTree(menuItems: MenuItem[]): MenuTreeNode[] {
    const topLevel = this.getTopLevelMenus(menuItems);
    
    return topLevel.map(item => this.buildTreeNode(item, menuItems));
  }
  
  private static buildTreeNode(item: MenuItem, allItems: MenuItem[]): MenuTreeNode {
    const children = this.getChildren(allItems, item.id);
    
    return {
      ...item,
      children: children.map(child => this.buildTreeNode(child, allItems))
    };
  }
}

/**
 * 菜单树节点接口（用于树形结构展示）
 */
export interface MenuTreeNode extends MenuItem {
  children: MenuTreeNode[];
}