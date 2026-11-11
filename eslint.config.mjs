import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Intentional in the UI layer: stores hydrate from localStorage in an effect, and the
      // shell uses plain <a> for full-page navigation. Kept as warnings so they stay visible
      // without blocking CI; revisit when the UI is next refactored.
      "react-hooks/set-state-in-effect": "warn",
      "@next/next/no-html-link-for-pages": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Not our source: Python venv, generated route types, local caches.
    ".venv/**",
    ".cache/**",
    "types/cache-life.d.ts",
    "types/root-params.d.ts",
    "types/routes.d.ts",
    "types/validator.ts",
  ]),
]);

export default eslintConfig;
