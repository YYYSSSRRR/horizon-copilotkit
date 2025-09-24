import axios from 'axios';
import { GenerateFunctionRequest, RAGStoreRequest, GenerateResponse } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
});

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

export const checkRecordedScript = async (filePath: string): Promise<{ exists: boolean; content: string; message?: string }> => {
  try {
    const response = await api.post('/playwright/check-script', { filePath });
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