import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // In dev the API runs on :8000; proxying keeps everything same-origin
      // so auth cookies behave exactly like they will in the single-service
      // production deployment.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // Split the heaviest third-party bundles into their own long-lived
        // cache entries, separate from app code that changes every deploy.
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("three") || id.includes("@react-three") || id.includes("postprocessing")) return "three";
          if (id.includes("recharts") || id.includes("d3-")) return "charts";
          if (id.includes("react-router") || id.includes("/react/") || id.includes("/react-dom/")) return "vendor-react";
          if (id.includes("@tanstack") || id.includes("axios")) return "vendor-query";
          if (id.includes("react-hook-form") || id.includes("@hookform") || id.includes("zod")) return "vendor-forms";
          return "vendor";
        },
      },
    },
  },
});
