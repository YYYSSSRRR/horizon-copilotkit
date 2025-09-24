#!/usr/bin/env node
/**
 * Function Generator Backend Server
 * 提供 Function 生成、Playwright 录制等服务
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const winston = require('winston');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

// 配置日志
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      return `${timestamp} - ${level.toUpperCase()} - ${message} ${Object.keys(meta).length ? JSON.stringify(meta) : ''}`;
    })
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({ 
      filename: 'access.log',
      format: winston.format.json()
    })
  ]
});

const app = express();

// 配置中间件
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 速率限制
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// 请求日志中间件
app.use((req, res, next) => {
  const start = Date.now();
  
  // 记录请求
  logger.info('Request', {
    method: req.method,
    url: req.originalUrl,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });
  
  // 在响应完成后记录
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info('Response', {
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration: `${duration}ms`
    });
    
    if (res.statusCode >= 400) {
      logger.warn('Error Response', {
        method: req.method,
        url: req.originalUrl,
        status: res.statusCode
      });
    }
  });
  
  next();
});

// 全局错误处理
app.use((err, req, res, next) => {
  logger.error('Unhandled Error', {
    error: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method
  });
  
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message
  });
});

// ============================================================================
// Playwright 录制相关 API
// ============================================================================

/**
 * 启动 Playwright 录制
 */
app.post('/api/playwright/record', async (req, res) => {
  try {
    const { url, savePath = './playwright-scripts', fileName = 'recorded-script.spec.js' } = req.body;
    
    logger.info('开始 Playwright 录制', { url, savePath, fileName });
    
    if (!url) {
      logger.warn('Playwright 录制失败: 缺少录制URL');
      return res.status(400).json({ error: '缺少录制URL' });
    }
    
    // 确保保存目录存在
    if (!fs.existsSync(savePath)) {
      fs.mkdirSync(savePath, { recursive: true });
    }
    
    const fullPath = path.join(savePath, fileName);
    
    // 使用 Playwright 命令行工具进行录制
    const cmd = [
      'npx',
      'playwright',
      'codegen',
      url,
      '--output',
      fullPath
    ];
    
    logger.info('执行命令', { cmd: cmd.join(' ') });
    
    // 启动录制进程
    const process = spawn(cmd[0], cmd.slice(1), {
      stdio: 'pipe',
      shell: true
    });
    
    logger.info('Playwright 录制进程已启动', { 
      pid: process.pid, 
      outputFile: fullPath 
    });
    
    res.json({
      success: true,
      message: 'Playwright 录制已启动，请在浏览器中执行操作。完成后关闭浏览器窗口。',
      filePath: fullPath,
      processId: process.pid
    });
    
  } catch (error) {
    logger.error('Playwright 录制失败', { error: error.message, stack: error.stack });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 检查录制的脚本
 */
app.post('/api/playwright/check-script', async (req, res) => {
  try {
    const { filePath } = req.body;
    
    logger.info('检查录制脚本', { filePath });
    
    if (!filePath || !fs.existsSync(filePath)) {
      logger.info('脚本文件不存在', { filePath });
      return res.json({ exists: false, content: '' });
    }
    
    const content = fs.readFileSync(filePath, 'utf-8');
    
    logger.info('脚本文件读取成功', { 
      filePath, 
      size: `${content.length} 字符` 
    });
    
    res.json({
      exists: true,
      content: content,
      message: '脚本录制完成'
    });
    
  } catch (error) {
    logger.error('检查录制脚本失败', { error: error.message, stack: error.stack });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 安装 Playwright 浏览器
 */
app.post('/api/playwright/install', async (req, res) => {
  try {
    logger.info('开始安装 Playwright 浏览器');
    
    const process = spawn('npx', ['playwright', 'install'], {
      stdio: 'pipe',
      shell: true
    });
    
    let stdout = '';
    let stderr = '';
    
    process.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    process.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        logger.info('Playwright 浏览器安装成功');
        res.json({
          success: true,
          message: 'Playwright 浏览器安装成功'
        });
      } else {
        logger.error('Playwright 浏览器安装失败', { stderr, code });
        res.status(500).json({
          success: false,
          error: stderr
        });
      }
    });
    
  } catch (error) {
    logger.error('安装 Playwright 浏览器失败', { error: error.message, stack: error.stack });
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// Function Generator 相关 API (待实现)
// ============================================================================

/**
 * 生成 LLM Function 定义和 Executor 代码
 */
app.post('/api/generate-function', async (req, res) => {
  try {
    // TODO: 实现函数生成逻辑
    res.json({
      success: true,
      functionDefinition: {},
      executorCode: '',
      ragRequest: {}
    });
  } catch (error) {
    logger.error('生成函数失败', { error: error.message });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 存储到 RAG 数据库
 */
app.post('/api/rag/store', async (req, res) => {
  try {
    // TODO: 实现 RAG 存储逻辑
    res.json({ success: true });
  } catch (error) {
    logger.error('存储到 RAG 失败', { error: error.message });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 导出文件
 */
app.get('/api/export/:type', async (req, res) => {
  try {
    const { type } = req.params;
    const { format = 'js' } = req.query;
    
    // TODO: 实现文件导出逻辑
    res.json({ success: true, type, format });
  } catch (error) {
    logger.error('导出文件失败', { error: error.message });
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// 健康检查
// ============================================================================

/**
 * 健康检查接口
 */
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'function-generator-backend',
    timestamp: new Date().toISOString()
  });
});

// ============================================================================
// 服务器启动
// ============================================================================

const PORT = process.env.SERVER_PORT || 5000;
const HOST = process.env.HOST || 'localhost';

app.listen(PORT, HOST, () => {
  const separator = '='.repeat(60);
  logger.info(separator);
  logger.info('Function Generator Backend Server 启动中...');
  logger.info(`服务器地址: http://${HOST}:${PORT}`);
  logger.info(`环境: ${process.env.NODE_ENV || 'development'}`);
  logger.info(`日志级别: ${process.env.LOG_LEVEL || 'info'}`);
  logger.info(separator);
  logger.info('可用的 API 端点:');
  logger.info('  POST /api/playwright/record      - 启动 Playwright 录制');
  logger.info('  POST /api/playwright/check-script - 检查录制的脚本');
  logger.info('  POST /api/playwright/install     - 安装 Playwright 浏览器');
  logger.info('  POST /api/generate-function      - 生成 LLM Function (待实现)');
  logger.info('  POST /api/rag/store              - 存储到 RAG 数据库 (待实现)');
  logger.info('  GET  /api/export/:type           - 导出文件 (待实现)');
  logger.info('  GET  /api/health                 - 健康检查');
  logger.info(separator);
});

// 优雅关闭
process.on('SIGTERM', () => {
  logger.info('收到 SIGTERM 信号，正在关闭服务器...');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('收到 SIGINT 信号，正在关闭服务器...');
  process.exit(0);
});

module.exports = app;