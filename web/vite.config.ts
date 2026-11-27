/// <reference types="vitest/config" />
import { cpSync } from "node:fs";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const contract = fileURLToPath(new URL("../shared/types/showcase.ts", import.meta.url));
const showcase = fileURLToPath(new URL("../site-data/showcase", import.meta.url));

/** Copies the committed showcase files into the build unchanged (FR-016; research R4). */
function copyShowcase(): Plugin {
  let outDir = "dist";
  return {
    name: "copy-showcase",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    closeBundle() {
      cpSync(showcase, `${outDir}/data/showcase`, { recursive: true });
    },
  };
}

export default defineConfig({
  base: process.env.GITHUB_PAGES === "1" ? "/travel-check/" : "/",
  plugins: [react(), copyShowcase()],
  resolve: { alias: { "@contract": contract } },
  build: { target: "es2022", sourcemap: false },
  preview: { port: 4173, strictPort: true },
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.ts", "tests/component/**/*.test.tsx"],
    setupFiles: ["tests/setup.ts"],
    restoreMocks: true,
  },
});
