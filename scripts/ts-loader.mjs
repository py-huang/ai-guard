// Node ESM loader hooks: run this repo's TypeScript route handlers without Next.js.
//   - resolves the "@/..." alias and extensionless relative imports
//   - stubs "server-only" (it only exists to fail client bundles)
//   - transpiles .ts/.tsx with the project's own `typescript`
import { existsSync, readFileSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "package.json"));
const ts = require("typescript");
const STUB = pathToFileURL(path.join(root, "scripts", "empty-module.mjs")).href;

function isFile(candidate) {
  return existsSync(candidate) && statSync(candidate).isFile();
}

function firstExisting(base) {
  for (const suffix of ["", ".ts", ".tsx", "/index.ts", "/index.tsx"]) {
    if (isFile(base + suffix)) {
      return base + suffix;
    }
  }
  return null;
}

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "server-only") {
    return { url: STUB, shortCircuit: true };
  }
  let base = null;
  if (specifier.startsWith("@/")) {
    base = path.join(root, specifier.slice(2));
  } else if ((specifier.startsWith("./") || specifier.startsWith("../")) && context.parentURL?.startsWith("file:")) {
    base = path.resolve(path.dirname(fileURLToPath(context.parentURL)), specifier);
  }
  if (base) {
    const found = firstExisting(base);
    if (found) {
      return { url: pathToFileURL(found).href, shortCircuit: true };
    }
  }
  return nextResolve(specifier, context);
}

export async function load(url, context, nextLoad) {
  if (url.startsWith("file:") && /\.(ts|tsx)$/.test(url) && !url.includes("/node_modules/")) {
    const file = fileURLToPath(url);
    const output = ts.transpileModule(readFileSync(file, "utf8"), {
      fileName: file,
      compilerOptions: {
        module: ts.ModuleKind.ESNext,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
        useDefineForClassFields: false,
      },
    });
    return { format: "module", source: output.outputText, shortCircuit: true };
  }
  return nextLoad(url, context);
}
