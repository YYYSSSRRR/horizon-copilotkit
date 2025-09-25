import axios from 'axios';
import { GenerateFunctionRequest, RAGStoreRequest, GenerateResponse } from '../types';

// 从环境变量读取后端配置
const BACKEND_HOST = import.meta.env.VITE_BACKEND_HOST || 'localhost';
const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '5000';
const API_BASE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api`;

console.log('API Configuration:', {
  BACKEND_HOST,
  BACKEND_PORT,
  API_BASE_URL
});

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器进行调试
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', {
      method: config.method,
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`
    });
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器进行调试
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      status: response.status,
      url: response.config.url,
      data: response.data
    });
    return response;
  },
  (error) => {
    console.error('API Response Error:', {
      message: error.message,
      status: error.response?.status,
      url: error.config?.url,
      data: error.response?.data
    });
    return Promise.reject(error);
  }
);

export const generateFunction = async (data: GenerateFunctionRequest): Promise<GenerateResponse> => {
  try {
    const response = await api.post('/generate-function', data);
    return response.data;
  } catch (error) {
    console.error('Generate function error:', error);
    throw error;
  }
};

export const storeToRAG = async (data: RAGStoreRequest): Promise<{ success: boolean }> => {
  try {
    const response = await api.post('/rag/store', data);
    return response.data;
  } catch (error) {
    console.error('Store to RAG error:', error);
    throw error;
  }
};

export const exportFile = async (type: 'function' | 'executor' | 'rag', format: 'js' | 'json' = 'js'): Promise<Blob> => {
  try {
    const response = await api.get(`/export/${type}`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    console.error('Export file error:', error);
    throw error;
  }
};

// Playwright 录制相关 API
export interface PlaywrightRecordRequest {
  url: string;
  savePath: string;
  fileName: string;
}

export interface PlaywrightRecordResponse {
  success: boolean;
  message: string;
  filePath: string;
  processId: number;
}

export const startPlaywrightRecord = async (data: PlaywrightRecordRequest): Promise<PlaywrightRecordResponse> => {
  try {
    const response = await api.post('/playwright/record', data);
    return response.data;
  } catch (error) {
    console.error('Playwright record error:', error);
    throw error;
  }
};

export const checkRecordedScript = async (filePath: string, processId?: number): Promise<{ exists: boolean; content: string; recording?: boolean; message?: string }> => {
  try {
    const response = await api.post('/playwright/check-script', { filePath, processId });
    return response.data;
  } catch (error) {
    console.error('Check recorded script error:', error);
    throw error;
  }
};

export const installPlaywright = async (): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await api.post('/playwright/install');
    return response.data;
  } catch (error) {
    console.error('Install Playwright error:', error);
    throw error;
  }
};