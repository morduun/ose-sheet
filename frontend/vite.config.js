import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    allowedHosts: ['ose.morduun.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        configure: (proxy) => {
          // Rewrite redirect Location headers from the backend's origin
          // to relative paths so the browser stays on the dev server origin
          // and preserves Authorization headers across redirects.
          proxy.on('proxyRes', (proxyRes) => {
            const location = proxyRes.headers['location'];
            if (location?.startsWith('http://localhost:8000')) {
              proxyRes.headers['location'] = location.replace('http://localhost:8000', '');
            }
          });
        },
      },
    }
  }
});
