import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwindcss()],base:'./',build:{outDir:'../../static/auth-v2',emptyOutDir:true,rollupOptions:{output:{entryFileNames:'auth.js',assetFileNames:asset=>asset.name?.endsWith('.css')?'auth.css':'[name][extname]'}}}});