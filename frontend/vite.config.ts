import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true, // expose on LAN so players can join from their phones
    proxy: {
      // 127.0.0.1, not localhost: if Docker Desktop is running this
      // project's own compose stack, its proxy squats on the IPv6 wildcard
      // for :8000 and "localhost" resolves there first on this machine —
      // silently routing every dev-server request to the stale containerized
      // backend instead of the one you're editing.
      '/api': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})
