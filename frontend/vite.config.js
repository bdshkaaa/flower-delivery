import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В режиме разработки (npm run dev) запросы /api/* уходят на backend,
// в docker-compose то же самое делает nginx (см. nginx.conf)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
