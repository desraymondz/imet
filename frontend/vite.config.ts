import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { VitePWA } from 'vite-plugin-pwa'


export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Reference: https://vite-pwa-org.netlify.app/guide/
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'iMet',
        short_name: 'iMet',
        description: 'Relationship Health Manager',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
    }),
  ],
  // Reference: https://vite.dev/config/server-options#server-proxy
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Remove the /api prefix from the path
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})