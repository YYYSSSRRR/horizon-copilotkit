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
 * Playwright 录制接口
 * 功能：启动 Playwright 的 codegen 工具来录制用户在浏览器中的操作
 * 生成对应的测试脚本文件
 */
app.post('/api/playwright/record', async (req, res) => {
  try {
    // 从请求体中获取参数，设置默认值
    let { url, savePath = './playwright-scripts', fileName = 'recorded-script.spec.js' } = req.body;

    // ========== URL 格式验证和处理 ==========
    if (!url) {
      logger.warn('Playwright 录制失败: 缺少录制URL');
      return res.status(400).json({ error: '缺少录制URL' });
    }

    // 自动添加协议前缀（默认使用 https）
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
      logger.info('自动添加 https 协议', { originalUrl: req.body.url, finalUrl: url });
    }

    // ========== 路径标准化和安全性检查 ==========
    // 规范化保存路径，防止路径遍历攻击
    const normalizedSavePath = path.resolve(savePath);
    
    // 基础安全检查：确保路径在当前工作目录或其子目录下
    const workingDir = process.cwd();
    if (!normalizedSavePath.startsWith(workingDir) && !path.isAbsolute(normalizedSavePath)) {
      // 如果不是绝对路径且不在工作目录下，则使用工作目录作为基准
      savePath = path.join(workingDir, savePath);
    } else {
      savePath = normalizedSavePath;
    }

    logger.info('开始 Playwright 录制', { 
      url, 
      originalSavePath: req.body.savePath,
      resolvedSavePath: savePath, 
      fileName 
    });

    // ========== 文件目录准备 ==========
    // 确保保存录制脚本的目录存在，如果不存在则递归创建
    try {
      if (!fs.existsSync(savePath)) {
        logger.info('创建保存目录', { savePath });
        fs.mkdirSync(savePath, { recursive: true, mode: 0o755 });
        logger.info('目录创建成功', { savePath });
      } else {
        logger.info('目录已存在', { savePath });
        
        // 检查目录是否可写
        try {
          fs.accessSync(savePath, fs.constants.W_OK);
        } catch (accessError) {
          logger.error('目录不可写', { savePath, error: accessError.message });
          return res.status(500).json({
            error: '保存目录不可写',
            details: `目录: ${savePath}`,
            suggestions: ['检查目录权限', '确保有写入权限']
          });
        }
      }
    } catch (dirError) {
      logger.error('创建保存目录失败', { 
        savePath, 
        error: dirError.message,
        code: dirError.code 
      });
      return res.status(500).json({
        error: '无法创建保存目录',
        details: `目录: ${savePath}, 错误: ${dirError.message}`,
        suggestions: [
          '检查路径是否有效',
          '检查是否有写入权限',
          '确保父目录存在且可访问',
          '检查磁盘空间是否充足'
        ]
      });
    }

    // 生成完整的文件保存路径
    const fullPath = path.join(savePath, fileName);

    // ========== Playwright 安装检查 ==========
    // 检查 Playwright 是否已正确安装
    try {
      const checkCmd = spawn('npx', ['playwright', '--version'], {
        stdio: 'pipe',  // 捕获输出
        shell: true
      });

      let versionOutput = '';
      // 收集版本信息输出
      checkCmd.stdout.on('data', (data) => {
        versionOutput += data.toString();
      });

      // 等待版本检查命令执行完成
      await new Promise((resolve, reject) => {
        checkCmd.on('close', (code) => {
          if (code !== 0) {
            reject(new Error('Playwright 未正确安装'));
          } else {
            logger.info('Playwright 版本检查', { version: versionOutput.trim() });
            resolve();
          }
        });
        
        checkCmd.on('error', (error) => {
          logger.error('Playwright 版本检查错误', { error: error.message });
          reject(error);
        });

        // 设置 5 秒超时防止命令卡住
        setTimeout(() => {
          checkCmd.kill();
          reject(new Error('Playwright 版本检查超时'));
        }, 5000);
      });
    } catch (error) {
      // Playwright 未安装或安装有问题时的错误处理
      logger.error('Playwright 检查失败', { error: error.message });
      return res.status(500).json({
        error: 'Playwright 未正确安装，请运行: npm install @playwright/test && npx playwright install'
      });
    }

    // ========== 浏览器安装检查 ==========
    // 检查 Playwright 的浏览器是否已安装
    try {
      const browserCheck = spawn('npx', ['playwright', 'install', '--dry-run'], {
        stdio: 'pipe',
        shell: true
      });

      let browserOutput = '';
      browserCheck.stdout.on('data', (data) => {
        browserOutput += data.toString();
      });

      // 等待浏览器检查完成
      await new Promise((resolve, reject) => {
        browserCheck.on('close', (code) => {
          logger.info('Playwright 浏览器检查', {
            code,
            output: browserOutput.trim()
          });
          resolve();
        });
        browserCheck.on('error', reject);

        // 10 秒超时
        setTimeout(() => {
          browserCheck.kill();
          reject(new Error('浏览器检查超时'));
        }, 10000);
      });
    } catch (error) {
      // 浏览器检查失败时只记录警告，不阻止后续执行
      logger.warn('Playwright 浏览器检查失败', { error: error.message });
    }

    // ========== 构建录制命令 ==========
    // 构建 Playwright codegen 命令参数
    const cmd = [
      'playwright',     // Playwright 命令
      'codegen',        // 代码生成/录制子命令
      url,              // 要录制的目标 URL
      '--output',       // 指定输出文件
      fullPath,         // 输出文件的完整路径
      '--target', 'javascript'  // 明确指定生成 JavaScript 代码
    ];

    logger.info('执行命令', { cmd: `npx ${cmd.join(' ')}` });

    // ========== 尝试获取 Playwright 路径 ==========
    // 先尝试获取 Playwright 的实际安装路径（用于调试）
    try {
      const whichCmd = spawn('where', ['playwright'], { stdio: 'pipe', shell: true });
      let pathOutput = '';
      whichCmd.stdout.on('data', (data) => {
        pathOutput += data.toString();
      });
      await new Promise((resolve) => {
        whichCmd.on('close', () => {
          if (pathOutput.trim()) {
            logger.info('找到 Playwright 路径', { path: pathOutput.trim() });
          }
          resolve();
        });
        setTimeout(resolve, 2000); // 2秒超时，避免卡住
      });
    } catch (error) {
      logger.warn('获取 Playwright 路径失败', { error: error.message });
    }

    // ========== 确定执行命令和参数 ==========
    let playwrightCmd = 'npx';
    let playwrightArgs = cmd;

    // 优先尝试使用项目本地安装的 playwright（性能更好）
    const localPlaywrightPath = path.join(process.cwd(), 'node_modules', '.bin', 'playwright');
    if (fs.existsSync(localPlaywrightPath)) {
      playwrightCmd = localPlaywrightPath;
      playwrightArgs = cmd.slice(1); // 去掉 'playwright' 参数，因为直接调用可执行文件
      logger.info('使用本地 Playwright 路径', { path: localPlaywrightPath });
    } else {
      logger.info('使用 npx Playwright');
    }

    // ========== 启动 Playwright 录制进程 ==========
    // 启动录制进程，配置详细的进程参数
    const childProcess = spawn(playwrightCmd, playwrightArgs, {
      stdio: ['ignore', 'pipe', 'pipe'], // 忽略 stdin，捕获 stdout 和 stderr
      shell: true,        // 使用 shell 执行
      detached: false,    // 不分离进程，保持父子关系
      env: {
        ...process.env,   // 继承当前进程的环境变量
        FORCE_COLOR: '0', // 禁用颜色输出
        // 清除可能有问题的环境变量
        PLAYWRIGHT_BROWSERS_PATH: undefined,
        // 明确设置一些关键的系统环境变量
        PATH: process.env.PATH,
        USERPROFILE: process.env.USERPROFILE, // Windows 用户目录
        HOME: process.env.HOME,               // Unix/Linux 用户目录
        APPDATA: process.env.APPDATA,         // Windows 应用数据目录
        LOCALAPPDATA: process.env.LOCALAPPDATA // Windows 本地应用数据目录
      },
      cwd: process.cwd(),   // 设置工作目录为当前目录
      windowsHide: false    // Windows 下不隐藏窗口，便于用户看到浏览器
    });

    // ========== 进程输出监听 ==========
    let stdoutData = '';
    let stderrData = '';

    // 监听标准输出（正常日志）
    childProcess.stdout.on('data', (data) => {
      const output = data.toString();
      stdoutData += output;
      logger.info('Playwright stdout:', output.trim());
    });

    // 监听标准错误输出（错误和警告信息）
    childProcess.stderr.on('data', (data) => {
      const output = data.toString();
      stderrData += output;
      logger.error('Playwright stderr:', output.trim());
    });

    // 监听进程启动错误
    childProcess.on('error', (error) => {
      logger.error('Playwright 进程错误', { error: error.message });
    });

    // 监听进程结束事件
    childProcess.on('close', (code, signal) => {
      logger.info('Playwright 录制进程结束', {
        code,           // 退出码
        signal,         // 终止信号
        outputFile: fullPath,
        stdout: stdoutData.trim(),
        stderr: stderrData.trim()
      });

      // 如果进程异常退出，记录可能的原因
      if (code !== 0) {
        logger.error('Playwright 执行失败', {
          exitCode: code,
          stderr: stderrData.trim(),
          possibleReasons: [
            '浏览器未安装或无法启动',
            'URL 无法访问',
            '权限不足',
            '显示服务器未运行 (Linux)',
            'Playwright 浏览器未安装'
          ]
        });
      }
    });

    // ========== 进程启动状态检查 ==========
    // 等待 3 秒确保进程正常启动
    await new Promise(resolve => setTimeout(resolve, 3000));

    // 检查进程是否还在运行
    if (childProcess.killed || childProcess.exitCode !== null) {
      // 进程启动失败的错误处理
      const errorMsg = `Playwright 录制进程启动失败 (退出码: ${childProcess.exitCode})`;
      logger.error(errorMsg, {
        killed: childProcess.killed,
        exitCode: childProcess.exitCode,
        stderr: stderrData.trim(),
        url: url,
        troubleshooting: {
          checkBrowsers: 'npx playwright install',
          testManually: `npx playwright codegen ${url}`,
          checkUrl: `curl -I ${url}`
        }
      });
      
      // 返回详细的错误信息和解决方案
      return res.status(500).json({
        error: errorMsg,
        details: stderrData.trim() || '无详细错误信息',
        troubleshooting: [
          '检查 URL 是否可访问',
          '运行: npx playwright install',
          '运行: npx playwright install chromium (如果只需要 Chrome)',
          '确保有图形界面环境',
          '检查防火墙设置'
        ],
        autoFix: '您可以尝试点击下方的"自动安装浏览器"按钮'
      });
    }

    // ========== 成功响应 ==========
    logger.info('Playwright 录制进程成功启动', {
      pid: childProcess.pid,  // 记录进程 ID
      outputFile: fullPath
    });

    // 返回成功响应
    res.json({
      success: true,
      message: 'Playwright 录制已启动，浏览器应该已经打开。请在浏览器中执行操作，完成后关闭浏览器窗口。',
      filePath: fullPath,      // 录制文件的保存路径
      processId: childProcess.pid // 进程 ID，可用于后续管理
    });

  } catch (error) {
    // ========== 全局错误处理 ==========
    logger.error('Playwright 录制失败', { 
      error: error.message, 
      stack: error.stack 
    });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 检查录制的脚本
 * 智能判断录制是否真正完成，避免读取未完成的文件
 */
app.post('/api/playwright/check-script', async (req, res) => {
  try {
    const { filePath, processId } = req.body;
    
    logger.info('检查录制脚本', { filePath, processId });
    
    // ========== 文件存在性检查 ==========
    if (!filePath || !fs.existsSync(filePath)) {
      logger.info('脚本文件不存在', { filePath });
      return res.json({ 
        exists: false, 
        content: '',
        recording: true,
        message: '录制进行中，文件尚未生成'
      });
    }
    
    // ========== 进程状态检查 ==========
    let processRunning = false;
    if (processId) {
      try {
        // 使用更可靠的方式检查进程状态
        processRunning = await checkProcessRunning(processId);
        if (processRunning) {
          logger.info('录制进程仍在运行', { processId });
        } else {
          logger.info('录制进程已结束', { processId });
        }
      } catch (error) {
        logger.warn('检查进程状态失败', { processId, error: error.message });
        processRunning = false;
      }
    }
    
    // ========== 文件内容和状态检查 ==========
    const stats = fs.statSync(filePath);
    const content = fs.readFileSync(filePath, 'utf-8');
    const contentTrimmed = content.trim();
    
    // 计算文件最后修改时间距离现在的时间差（毫秒）
    const timeSinceLastModified = Date.now() - stats.mtime.getTime();
    
    logger.info('文件状态检查', { 
      filePath,
      fileSize: stats.size,
      contentLength: contentTrimmed.length,
      lastModified: stats.mtime,
      timeSinceLastModified: `${timeSinceLastModified}ms`,
      processRunning
    });
    
    // ========== 录制完成判断逻辑 ==========
    const isRecordingComplete = checkRecordingComplete(contentTrimmed, timeSinceLastModified, processRunning);
    
    if (isRecordingComplete.complete) {
      logger.info('录制已完成', { 
        filePath, 
        reason: isRecordingComplete.reason,
        contentSize: `${contentTrimmed.length} 字符` 
      });
      
      res.json({
        exists: true,
        content: contentTrimmed,
        recording: false,
        message: isRecordingComplete.message
      });
    } else {
      logger.info('录制仍在进行中', { 
        filePath, 
        reason: isRecordingComplete.reason 
      });
      
      res.json({
        exists: true,
        content: contentTrimmed,
        recording: true,
        message: isRecordingComplete.message
      });
    }
    
  } catch (error) {
    logger.error('检查录制脚本失败', { error: error.message, stack: error.stack });
    res.status(500).json({ error: error.message });
  }
});

/**
 * 检查进程是否正在运行
 * 使用跨平台的方式来检查进程状态
 * @param {number} pid - 进程ID
 * @returns {Promise<boolean>} - 进程是否运行中
 */
async function checkProcessRunning(pid) {
  if (!pid || pid <= 0) {
    return false;
  }

  try {
    // 方法1: 尝试使用 process.kill(pid, 0) 检查
    try {
      process.kill(pid, 0);
      
      // 进程存在，但需要进一步验证是否是 Playwright 进程
      const isPlaywrightProcess = await verifyPlaywrightProcess(pid);
      return isPlaywrightProcess;
    } catch (error) {
      if (error.code === 'ESRCH') {
        // No such process - 进程不存在
        return false;
      } else if (error.code === 'EPERM') {
        // Operation not permitted - 进程存在但没权限，认为还在运行
        const isPlaywrightProcess = await verifyPlaywrightProcess(pid);
        return isPlaywrightProcess;
      } else {
        throw error;
      }
    }
  } catch (error) {
    // 如果 process.kill 方法失败，尝试其他方法
    try {
      return await checkProcessByCommand(pid);
    } catch (cmdError) {
      // 所有方法都失败，保守地认为进程已结束
      logger.warn('所有进程检查方法都失败，假定进程已结束', { 
        pid, 
        killError: error.message, 
        cmdError: cmdError.message 
      });
      return false;
    }
  }
}

/**
 * 验证进程是否为 Playwright 相关进程
 * @param {number} pid - 进程ID
 * @returns {Promise<boolean>}
 */
async function verifyPlaywrightProcess(pid) {
  try {
    // 根据操作系统使用不同的命令来检查进程详情
    const platform = process.platform;
    let cmd, args;
    
    if (platform === 'win32') {
      // Windows: 使用 tasklist
      cmd = 'tasklist';
      args = ['/FI', `PID eq ${pid}`, '/FO', 'CSV', '/NH'];
    } else {
      // Unix/Linux/macOS: 使用 ps
      cmd = 'ps';
      args = ['-p', pid.toString(), '-o', 'comm='];
    }
    
    return new Promise((resolve) => {
      const process = spawn(cmd, args, { stdio: 'pipe', shell: true });
      let output = '';
      
      process.stdout.on('data', (data) => {
        output += data.toString();
      });
      
      process.on('close', (code) => {
        if (code !== 0) {
          // 命令执行失败，进程可能不存在
          resolve(false);
          return;
        }
        
        const outputLower = output.toLowerCase();
        // 检查输出是否包含 playwright 或 node 相关关键词
        const isPlaywright = outputLower.includes('playwright') || 
                            outputLower.includes('node') || 
                            outputLower.includes('npx') ||
                            outputLower.includes('chrome') ||
                            outputLower.includes('chromium');
        
        resolve(isPlaywright);
      });
      
      // 3秒超时
      setTimeout(() => {
        process.kill();
        resolve(false);
      }, 3000);
    });
  } catch (error) {
    logger.warn('验证 Playwright 进程失败', { pid, error: error.message });
    return true; // 保守地认为是 Playwright 进程
  }
}

/**
 * 使用系统命令检查进程状态
 * @param {number} pid - 进程ID
 * @returns {Promise<boolean>}
 */
async function checkProcessByCommand(pid) {
  return new Promise((resolve) => {
    const platform = process.platform;
    let cmd, args;
    
    if (platform === 'win32') {
      cmd = 'tasklist';
      args = ['/FI', `PID eq ${pid}`];
    } else {
      cmd = 'ps';
      args = ['-p', pid.toString()];
    }
    
    const process = spawn(cmd, args, { stdio: 'pipe', shell: true });
    
    process.on('close', (code) => {
      // 退出码为0表示进程存在
      resolve(code === 0);
    });
    
    process.on('error', () => {
      resolve(false);
    });
    
    // 5秒超时
    setTimeout(() => {
      process.kill();
      resolve(false);
    }, 5000);
  });
}

/**
 * 检查录制是否完成的智能判断函数
 * @param {string} content - 文件内容
 * @param {number} timeSinceLastModified - 距离最后修改的时间（毫秒）
 * @param {boolean} processRunning - 进程是否还在运行
 * @returns {object} - { complete: boolean, reason: string, message: string }
 */
function checkRecordingComplete(content, timeSinceLastModified, processRunning) {
  // 如果内容为空，肯定还没完成
  if (!content || content.length === 0) {
    return {
      complete: false,
      reason: '文件内容为空',
      message: '录制进行中，等待内容生成...'
    };
  }
  
  // 检查是否包含 Playwright 的基本结构
  const hasPlaywrightImports = content.includes('test(') || 
                               content.includes('page.') || 
                               content.includes('await page') ||
                               content.includes('import { test, expect }');
  
  if (!hasPlaywrightImports) {
    return {
      complete: false,
      reason: '缺少 Playwright 基本结构',
      message: '录制进行中，等待脚本生成...'
    };
  }
  
  // 检查是否包含完整的测试结构
  const hasTestStructure = content.includes('test(') && 
                          (content.includes('await page.goto') || content.includes('page.goto')) &&
                          content.includes('}');
  
  if (!hasTestStructure) {
    return {
      complete: false,
      reason: '测试结构不完整',
      message: '录制进行中，脚本结构生成中...'
    };
  }
  
  // 如果进程还在运行，需要额外检查
  if (processRunning) {
    // 如果文件在最近5秒内还在修改，认为还在录制中
    if (timeSinceLastModified < 5000) {
      return {
        complete: false,
        reason: '文件最近还在修改中',
        message: '录制进行中，请继续操作...'
      };
    }
    
    // 如果进程在运行但文件很久没更新了，可能用户还在操作中
    if (timeSinceLastModified < 30000) { // 30秒内
      return {
        complete: false,
        reason: '录制进程运行中',
        message: '录制进行中，等待用户操作...'
      };
    }
  }
  
  // 进程已结束且有完整内容，认为录制完成
  if (!processRunning && hasTestStructure) {
    return {
      complete: true,
      reason: '录制进程已结束且内容完整',
      message: '脚本录制完成！'
    };
  }
  
  // 文件很长时间没有修改了，且内容看起来完整，可能已经完成
  if (timeSinceLastModified > 10000 && hasTestStructure && content.length > 100) {
    return {
      complete: true,
      reason: '文件长时间未修改且内容完整',
      message: '脚本录制完成！'
    };
  }
  
  // 默认认为还在录制中
  return {
    complete: false,
    reason: '等待录制完成',
    message: '录制进行中，请继续在浏览器中操作...'
  };
}

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