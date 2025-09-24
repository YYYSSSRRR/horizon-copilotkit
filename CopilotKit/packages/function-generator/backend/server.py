#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Function Generator Backend Server
提供 Function 生成、Playwright 录制等服务
"""
import os
import subprocess
import logging
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('access.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)
access_logger = logging.getLogger('access')

app = FastAPI(
    title="Function Generator Backend",
    description="提供 Function 生成、Playwright 录制等服务",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型定义
class PlaywrightRecordRequest(BaseModel):
    url: str
    savePath: Optional[str] = './playwright-scripts'
    fileName: Optional[str] = 'recorded-script.spec.js'

class CheckScriptRequest(BaseModel):
    filePath: str


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求和响应信息"""
    start_time = time.time()
    
    # 记录请求信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get('user-agent', 'Unknown')
    access_logger.info(
        f"[REQUEST] {request.method} {request.url} - "
        f"Client: {client_ip} - User-Agent: {user_agent}"
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    duration = time.time() - start_time
    access_logger.info(
        f"[RESPONSE] {request.method} {request.url} - "
        f"Status: {response.status_code} - Duration: {duration:.3f}s"
    )
    
    if response.status_code >= 400:
        access_logger.warning(
            f"[ERROR_RESPONSE] {request.method} {request.url} - "
            f"Status: {response.status_code}"
        )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    access_logger.error(
        f"[EXCEPTION] {request.method} {request.url} - Error: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={'error': 'Internal Server Error', 'message': str(exc)}
    )


# ============================================================================
# Playwright 录制相关 API
# ============================================================================

@app.post('/api/playwright/record')
async def start_playwright_record(request: PlaywrightRecordRequest):
    """启动 Playwright 录制"""
    try:
        url = request.url
        save_path = request.savePath
        file_name = request.fileName
        
        logger.info(
            f"开始 Playwright 录制 - URL: {url}, "
            f"保存路径: {save_path}, 文件名: {file_name}"
        )
        
        if not url:
            logger.warning("Playwright 录制失败: 缺少录制URL")
            raise HTTPException(status_code=400, detail='缺少录制URL')
            
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        full_path = os.path.join(save_path, file_name)
        
        # 使用 Playwright 命令行工具进行录制
        cmd = [
            'npx',
            'playwright',
            'codegen',
            url,
            '--output',
            full_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        # 启动录制进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(
            f"Playwright 录制进程已启动 - PID: {process.pid}, 输出文件: {full_path}"
        )
        
        return {
            'success': True,
            'message': 'Playwright 录制已启动，请在浏览器中执行操作。完成后关闭浏览器窗口。',
            'filePath': full_path,
            'processId': process.pid
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playwright 录制失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/playwright/check-script')
async def check_recorded_script(request: CheckScriptRequest):
    """检查录制的脚本"""
    try:
        file_path = request.filePath
        
        logger.info(f"检查录制脚本 - 文件路径: {file_path}")
        
        if not file_path or not os.path.exists(file_path):
            logger.info(f"脚本文件不存在: {file_path}")
            return {'exists': False, 'content': ''}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.info(f"脚本文件读取成功 - 文件大小: {len(content)} 字符")
            
        return {
            'exists': True,
            'content': content,
            'message': '脚本录制完成'
        }
        
    except Exception as e:
        logger.error(f"检查录制脚本失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/playwright/install')
async def install_playwright():
    """安装 Playwright 浏览器"""
    try:
        logger.info("开始安装 Playwright 浏览器")
        cmd = ['npx', 'playwright', 'install']
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            logger.info("Playwright 浏览器安装成功")
            return {
                'success': True,
                'message': 'Playwright 浏览器安装成功'
            }
        else:
            logger.error(
                f"Playwright 浏览器安装失败 - stderr: {process.stderr}"
            )
            raise HTTPException(
                status_code=500,
                detail={
                    'success': False,
                    'error': process.stderr
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"安装 Playwright 浏览器失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Function Generator 相关 API (待实现)
# ============================================================================

@app.post('/api/generate-function')
async def generate_function():
    """生成 LLM Function 定义和 Executor 代码"""
    try:
        # TODO: 实现函数生成逻辑
        return {
            'success': True,
            'functionDefinition': {},
            'executorCode': '',
            'ragRequest': {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/rag/store')
async def store_to_rag():
    """存储到 RAG 数据库"""
    try:
        # TODO: 实现 RAG 存储逻辑
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/export/{export_type}')
async def export_file(export_type: str, format: str = 'js'):
    """导出文件"""
    try:
        # TODO: 实现文件导出逻辑
        return {'success': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 健康检查
# ============================================================================

@app.get('/api/health')
async def health_check():
    """健康检查接口"""
    return {
        'status': 'healthy',
        'service': 'function-generator-backend'
    }


if __name__ == '__main__':
    import uvicorn
    
    port = int(os.getenv('SERVER_PORT', 5000))
    host = os.getenv('HOST', 'localhost')
    
    logger.info("=" * 60)
    logger.info("Function Generator Backend Server 启动中...")
    logger.info(f"服务器地址: http://{host}:{port}")
    logger.info(f"调试模式: {os.getenv('FLASK_DEBUG', '0') == '1'}")
    logger.info(f"日志级别: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info("=" * 60)
    logger.info("可用的 API 端点:")
    logger.info("  POST /api/playwright/record      - 启动 Playwright 录制")
    logger.info("  POST /api/playwright/check-script - 检查录制的脚本")
    logger.info("  POST /api/playwright/install     - 安装 Playwright 浏览器")
    logger.info("  POST /api/generate-function      - 生成 LLM Function (待实现)")
    logger.info("  POST /api/rag/store              - 存储到 RAG 数据库 (待实现)")
    logger.info("  GET  /api/export/{type}          - 导出文件 (待实现)")
    logger.info("  GET  /api/health                 - 健康检查")
    logger.info("  GET  /docs                       - API 文档")
    logger.info("=" * 60)
    
    try:
        uvicorn.run(
            "server:app",
            host=host,
            port=port,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}", exc_info=True)
        raise