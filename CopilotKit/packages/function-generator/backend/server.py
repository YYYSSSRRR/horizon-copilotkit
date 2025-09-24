#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Function Generator Backend Server
提供 Function 生成、Playwright 录制等服务
"""
import os
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


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
        
        if not url:
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
        
        # 启动录制进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Playwright 录制已启动，请在浏览器中执行操作。完成后关闭浏览器窗口。',
            'filePath': full_path,
            'processId': process.pid
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/playwright/check-script', methods=['POST'])
def check_recorded_script():
    """检查录制的脚本"""
    try:
        data = request.get_json()
        file_path = data.get('filePath')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'exists': False, 'content': ''})
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return jsonify({
            'exists': True,
            'content': content,
            'message': '脚本录制完成'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/playwright/install', methods=['POST'])
def install_playwright():
    """安装 Playwright 浏览器"""
    try:
        cmd = ['npx', 'playwright', 'install']
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Playwright 浏览器安装成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': process.stderr
            }), 500
            
    except Exception as e:
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
    host = os.getenv('HOST', '127.0.0.1')
    app.run(debug=True, port=port, host=host)