import { defineConfig } from 'vite';

export default defineConfig({
  // Tauri expects a fixed port
  server: {
    port: 1420,
    strictPort: true,
  },
  // Build output for Tauri
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'esnext',
  },
  // Prevent vite from obscuring rust errors
  clearScreen: false,
});
