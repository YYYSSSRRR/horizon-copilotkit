#!/usr/bin/env ts-node

import { MenuConfigTransformer } from '../src/menu-transformers';
import { MenuItem } from '../src/types';
import * as path from 'path';

async function transformMenuConfig() {
  console.log('🔄 菜单配置转换工具');
  console.log('=====================================');

  try {
    // 转换菜单配置文件
    const configPath = path.join(__dirname, 'menus-config.json');
    console.log(`📁 读取配置文件: ${configPath}`);
    
    const menuItems = await MenuConfigTransformer.transformFromFile(configPath);
    
    console.log(`✅ 转换完成，共生成 ${menuItems.length} 个菜单项\n`);
    
    // 显示转换结果
    console.log('📋 转换结果预览:');
    console.log('=====================================');
    
    // 显示前10个菜单项
    const previewItems = menuItems.slice(0, 10);
    previewItems.forEach((item, index) => {
      console.log(`${index + 1}. ${item.text} (ID: ${item.id})`);
      console.log(`   Level: ${item.level}, Parent: ${item.parentId || 'none'}`);
      console.log(`   Emit: [${item.emit?.map(e => `"${e}"`).join(', ') || ''}]`);
      console.log(`   HasSubmenu: ${item.hasSubmenu}\n`);
    });
    
    if (menuItems.length > 10) {
      console.log(`... 还有 ${menuItems.length - 10} 个菜单项\n`);
    }
    
    // 生成TypeScript代码
    console.log('📝 生成TypeScript代码:');
    console.log('=====================================');
    
    const tsCode = generateTypeScriptCode(menuItems);
    console.log(tsCode);
    
    // 统计信息
    console.log('\n📊 统计信息:');
    console.log('=====================================');
    const topLevel = MenuConfigTransformer.getTopLevelMenus(menuItems);
    console.log(`顶级菜单: ${topLevel.length} 个`);
    
    const byLevel = menuItems.reduce((acc, item) => {
      acc[item.level] = (acc[item.level] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);
    
    console.log('各层级菜单分布:');
    Object.keys(byLevel).forEach(level => {
      console.log(`  Level ${level}: ${byLevel[parseInt(level)]} 个`);
    });
    
    const withEmit = menuItems.filter(item => item.emit && item.emit.length > 0);
    console.log(`有emit动作的菜单: ${withEmit.length} 个`);
    
    const withSubmenu = menuItems.filter(item => item.hasSubmenu);
    console.log(`有子菜单的菜单: ${withSubmenu.length} 个`);
    
    // 树形结构展示（仅展示顶级菜单）
    console.log('\n🌳 菜单树结构:');
    console.log('=====================================');
    const tree = MenuConfigTransformer.toTree(menuItems);
    tree.slice(0, 3).forEach(node => {
      printTreeNode(node, 0);
    });
    
    if (tree.length > 3) {
      console.log(`... 还有 ${tree.length - 3} 个顶级菜单\n`);
    }
    
  } catch (error) {
    console.error('❌ 转换失败:', error);
  }
}

function generateTypeScriptCode(menuItems: MenuItem[]): string {
  let code = 'const menuItems: MenuItem[] = [\n';
  
  menuItems.forEach(item => {
    code += '  {\n';
    code += `    id: '${item.id}',\n`;
    code += `    text: '${item.text}',\n`;
    code += `    level: ${item.level},\n`;
    if (item.parentId) {
      code += `    parentId: '${item.parentId}',\n`;
    }
    code += `    hasSubmenu: ${item.hasSubmenu}`;
    
    if (item.emit && item.emit.length > 0) {
      code += ',\n';
      code += `    emit: [${item.emit.map(e => `'${e}'`).join(', ')}]\n`;
    } else {
      code += '\n';
    }
    
    code += '  },\n';
  });
  
  code += '];';
  return code;
}

function printTreeNode(node: any, indent: number): void {
  const prefix = '  '.repeat(indent);
  console.log(`${prefix}├─ ${node.text} (${node.id})`);
  
  if (node.children && node.children.length > 0) {
    node.children.slice(0, 2).forEach((child: any) => {
      printTreeNode(child, indent + 1);
    });
    if (node.children.length > 2) {
      console.log(`${prefix}   ... 还有 ${node.children.length - 2} 个子菜单`);
    }
  }
}

// 运行转换
if (require.main === module) {
  transformMenuConfig().catch(console.error);
}

export { transformMenuConfig };