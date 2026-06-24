import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:6020',
        changeOrigin: true,
        ws: true,
      },
      '/output': {
        target: 'http://127.0.0.1:6020',
        changeOrigin: true,
      },
    },
  },
})
