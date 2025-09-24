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
from flask import Flask, request, jsonify, g
from flask_cors import CORS

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

app = Flask(__name__)
CORS(app)


@app.before_request
def log_request_info():
    """记录请求开始时间和信息"""
    g.start_time = time.time()
    access_logger.info(f"[REQUEST] {request.method} {request.url} - Client: {request.remote_addr} - User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    if request.is_json and request.get_json():
        # 只记录非敏感数据
        data = request.get_json()
        safe_data = {k: v for k, v in data.items() if k not in ['password', 'token', 'secret']}
        if safe_data:
            access_logger.info(f"[REQUEST_DATA] {safe_data}")


@app.after_request
def log_response_info(response):
    """记录响应信息"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        access_logger.info(f"[RESPONSE] {request.method} {request.url} - Status: {response.status_code} - Duration: {duration:.3f}s")
        if response.status_code >= 400:
            access_logger.warning(f"[ERROR_RESPONSE] {request.method} {request.url} - Status: {response.status_code} - Response: {response.get_data(as_text=True)[:200]}")
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理"""
    access_logger.error(f"[EXCEPTION] {request.method} {request.url} - Error: {str(e)}", exc_info=True)
    return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


# ============================================================================
# Playwright 录制相关 API
# ============================================================================

@app.route('/api/playwright/record', methods=['POST'])
def start_playwright_record():
    """启动 Playwright 录制"""
    try:
        data = request.get_json()
        url = data.get('url')
        save_path = data.get('savePath', './playwright-scripts')
        file_name = data.get('fileName', 'recorded-script.spec.js')
        
        logger.info(f"开始 Playwright 录制 - URL: {url}, 保存路径: {save_path}, 文件名: {file_name}")
        
        if not url:
            logger.warning("Playwright 录制失败: 缺少录制URL")
            return jsonify({'error': '缺少录制URL'}), 400
            
        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        full_path = os.path.join(save_path, file_name)
        
        # 使用 Playwright 命令行工具进行录制
        # 这里使用 codegen 命令来生成脚本
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
        
        logger.info(f"Playwright 录制进程已启动 - PID: {process.pid}, 输出文件: {full_path}")
        
        return jsonify({
            'success': True,
            'message': 'Playwright 录制已启动，请在浏览器中执行操作。完成后关闭浏览器窗口。',
            'filePath': full_path,
            'processId': process.pid
        })
        
    except Exception as e:
        logger.error(f"Playwright 录制失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/playwright/check-script', methods=['POST'])
def check_recorded_script():
    """检查录制的脚本"""
    try:
        data = request.get_json()
        file_path = data.get('filePath')
        
        logger.info(f"检查录制脚本 - 文件路径: {file_path}")
        
        if not file_path or not os.path.exists(file_path):
            logger.info(f"脚本文件不存在: {file_path}")
            return jsonify({'exists': False, 'content': ''})
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.info(f"脚本文件读取成功 - 文件大小: {len(content)} 字符")
            
        return jsonify({
            'exists': True,
            'content': content,
            'message': '脚本录制完成'
        })
        
    except Exception as e:
        logger.error(f"检查录制脚本失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/playwright/install', methods=['POST'])
def install_playwright():
    """安装 Playwright 浏览器"""
    try:
        logger.info("开始安装 Playwright 浏览器")
        cmd = ['npx', 'playwright', 'install']
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            logger.info("Playwright 浏览器安装成功")
            return jsonify({
                'success': True,
                'message': 'Playwright 浏览器安装成功'
            })
        else:
            logger.error(f"Playwright 浏览器安装失败 - stderr: {process.stderr}")
            return jsonify({
                'success': False,
                'error': process.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"安装 Playwright 浏览器失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Function Generator 相关 API (待实现)
# ============================================================================

@app.route('/api/generate-function', methods=['POST'])
def generate_function():
    """生成 LLM Function 定义和 Executor 代码"""
    try:
        data = request.get_json()
        # TODO: 实现函数生成逻辑
        return jsonify({
            'success': True,
            'functionDefinition': {},
            'executorCode': '',
            'ragRequest': {}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/store', methods=['POST'])
def store_to_rag():
    """存储到 RAG 数据库"""
    try:
        data = request.get_json()
        # TODO: 实现 RAG 存储逻辑
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<export_type>', methods=['GET'])
def export_file(export_type):
    """导出文件"""
    try:
        format_type = request.args.get('format', 'js')
        # TODO: 实现文件导出逻辑
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 健康检查
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'service': 'function-generator-backend'
    })


if __name__ == '__main__':
    import os
    port = int(os.getenv('SERVER_PORT', 5000))
    host = os.getenv('HOST', 'localhost')
    
    try:
        app.run(debug=True, port=port, host=host)
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}", exc_info=True)
        raise