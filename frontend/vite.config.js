import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/products': 'http://localhost:8000',
      '/customers': 'http://localhost:8000',
      '/suppliers': 'http://localhost:8000',
      '/orders': 'http://localhost:8000',
      '/credit': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
})
