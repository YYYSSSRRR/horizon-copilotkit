import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@copilotkit/react-core-next': fileURLToPath(new URL('../../react-core-next/src', import.meta.url)),
      '@copilotkit/shared': fileURLToPath(new URL('../../shared/src', import.meta.url)),
      '@copilotkit/playwright-actuator': fileURLToPath(new URL('../../playwright-actuator/src', import.meta.url)),
      // openinula 映射到 react
      'react$': 'openinula',
      'react-dom$': 'openinula', 
      'react-is$': 'openinula',
      'react/jsx-runtime': fileURLToPath(new URL('../node_modules/openinula/jsx-runtime.js', import.meta.url)),
      'react/jsx-dev-runtime': fileURLToPath(new URL('../node_modules/openinula/jsx-dev-runtime.js', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8005',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },
}) 