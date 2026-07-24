/// <reference types="vitest" />
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The API base is injected at build time via VITE_API_BASE (empty = same origin,
// which is how the backend serves the built SPA in P3).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@tokens": fileURLToPath(new URL("./src/tokens", import.meta.url)),
      "@ui": fileURLToPath(new URL("./src/ui", import.meta.url)),
      "@lib": fileURLToPath(new URL("./src/lib", import.meta.url)),
    },
  },
  build: { outDir: "dist", sourcemap: false },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
