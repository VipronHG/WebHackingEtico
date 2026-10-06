import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Funciona bien en GitHub Pages aunque el sitio esté dentro de /nombre-del-repo/
  base: './'
})
