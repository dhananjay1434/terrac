/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The API base is injected at build time via VITE_API_BASE (empty = same origin,
// which is how the backend serves the built SPA in P3).
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
