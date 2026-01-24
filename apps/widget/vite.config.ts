import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [preact()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  build: {
    // Build as a single IIFE bundle for embedding
    lib: {
      entry: resolve(__dirname, 'src/main.tsx'),
      name: 'RevaWidget',
      fileName: 'reva-widget',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        // Ensure CSS is injected into JS
        assetFileNames: 'reva-widget.[ext]',
      },
    },
    // Minify for production (use esbuild, default in Vite)
    minify: 'esbuild',
  },
  define: {
    // Define the API URL at build time
    'import.meta.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:8000'
    ),
  },
});
