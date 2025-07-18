import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // 开发服务器配置
  server: {
    port: 3000,
    host: true,
    open: true,
    cors: true,
    strictPort: false, // 如果端口被占用，会自动找下一个可用端口
  },

  // 预览服务器配置
  preview: {
    port: 3000,
    host: true,
  },

  // 构建配置
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          copilotkit: ['@copilotkit/react-core', '@copilotkit/react-ui'],
        },
      },
    },
  },

  // 路径别名
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // 优化配置
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@copilotkit/react-core',
      '@copilotkit/react-ui',
      '@copilotkit/shared',
      'lucide-react'
    ],
  },

  // CSS 配置
  css: {
    postcss: './postcss.config.js',
  },

  // 环境变量配置
  define: {
    __BACKEND_URL__: JSON.stringify(process.env.VITE_BACKEND_URL || 'http://localhost:3001'), // 后端端口保持 3001
  },
}) 