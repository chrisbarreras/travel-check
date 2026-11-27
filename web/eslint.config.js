// @ts-check
import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

/** Data may be loaded only inside src/data/ (FR-011; contracts/data-access.md, Enforcement). */
export const dataAccessRules = {
  "no-restricted-globals": [
    "error",
    { name: "fetch", message: "Load data through src/data/ (DataSource), not fetch." },
    { name: "XMLHttpRequest", message: "Load data through src/data/ (DataSource)." },
  ],
  "no-restricted-properties": [
    "error",
    { object: "window", property: "fetch", message: "Load data through src/data/." },
    { object: "globalThis", property: "fetch", message: "Load data through src/data/." },
  ],
  "no-restricted-imports": [
    "error",
    { patterns: [{ group: ["**/site-data/**"], message: "Load data through src/data/." }] },
  ],
};

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "src/data/generated",
      "test-results",
      "playwright-report",
      ".lighthouseci",
      "tests/fixtures/lint",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
      globals: { ...globals.browser },
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks, "jsx-a11y": jsxA11y },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.strict.rules,
      ...dataAccessRules,
    },
  },
  {
    files: ["src/data/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-globals": "off",
      "no-restricted-properties": "off",
    },
  },
  {
    files: ["scripts/**/*.mjs", "eslint.config.js"],
    ...tseslint.configs.disableTypeChecked,
  },
  {
    files: ["scripts/**/*.mjs", "*.config.{js,ts}", "eslint.config.js"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    files: ["tests/**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
);
