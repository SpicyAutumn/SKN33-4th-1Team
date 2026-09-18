import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Local review only: reuse the existing API without exposing a new backend port.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (proxyRequest, request) => {
            // Keep unrecognized origins intact so the backend can reject them.
            if (request.headers.origin === 'http://127.0.0.1:5174') {
              proxyRequest.setHeader('Origin', 'http://127.0.0.1:8081');
              proxyRequest.setHeader('Referer', 'http://127.0.0.1:8081/');
            }
          });
        },
      },
    },
  },
});
