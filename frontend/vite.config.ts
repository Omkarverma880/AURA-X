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
    // No manualChunks on purpose.
    //
    // This previously split node_modules into named vendor chunks for
    // long-lived caching, including a "three" chunk. That backfired: forcing
    // a manual chunk makes it a *static* dependency of the entry, so
    // three.js ended up in index.html's modulepreload list and every visitor
    // downloaded ~1MB of WebGL - even opening /dashboard, which never
    // renders a scene. The 3D code is only imported by the lazily-loaded
    // Landing route, so rollup's default splitting keeps it behind that
    // dynamic boundary where it belongs.
    //
    // Measured on first paint (sum of index.html's preloaded chunks):
    //   manualChunks : 2504K across 11 chunks
    //   default      :  903K across 15 chunks
    //
    // If manual chunking is reintroduced for cache granularity, re-check
    // with:  grep -o 'assets/[^"]*\.js' dist/index.html
    // three-*.js must not appear in that list.
  },
});
