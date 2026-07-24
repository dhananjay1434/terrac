// Flat config (required by eslint 9+). Line-cap rules are WARNINGS only —
// they guide new code without failing lint on existing files.
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";

export default [
  {
    ignores: ["dist/**", "node_modules/**", "*.config.*"],
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: { browser: true },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      "max-lines": ["warn", 300],
      "max-lines-per-function": ["warn", 50],
      // Downgraded to "warn" (existing code trips these; this task adds the
      // linter non-blockingly, it does not fix pre-existing code).
      "@typescript-eslint/no-unused-vars": "warn",
      "react-hooks/set-state-in-effect": "warn",
      // Evidence video thumbnails are intentionally silent/no-caption previews.
      "jsx-a11y/media-has-caption": "warn",
    },
  },
];
