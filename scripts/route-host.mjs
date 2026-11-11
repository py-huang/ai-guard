// Serves the app/api route handlers over plain HTTP without Next.js.
//
//   node scripts/route-host.mjs --port 13000
//
// It loads the real route.ts files, so it exercises the same code Next runs. It does not
// apply next.config.ts headers or Next's own routing, so it is a smoke/CI aid, not a server.
import { readdirSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { register } from "node:module";
import path from "node:path";
import { Readable } from "node:stream";
import { fileURLToPath, pathToFileURL } from "node:url";

register("./ts-loader.mjs", import.meta.url);

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portIndex = process.argv.indexOf("--port");
const port = portIndex > -1 ? Number(process.argv[portIndex + 1]) : 3000;

function findRoutes(dir, found = []) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      findRoutes(full, found);
    } else if (name === "route.ts") {
      found.push(full);
    }
  }
  return found;
}

const apiRoot = path.join(root, "app");
const routes = new Map();
for (const file of findRoutes(path.join(apiRoot, "api"))) {
  const route = "/" + path.relative(apiRoot, path.dirname(file)).split(path.sep).join("/");
  routes.set(route, await import(pathToFileURL(file).href));
}

createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`);
  const routeModule = routes.get(url.pathname);
  const handler = routeModule?.[req.method ?? "GET"];
  if (!handler) {
    res.writeHead(routeModule ? 405 : 404).end();
    return;
  }
  try {
    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const request = new Request(url, {
      method: req.method,
      headers: req.headers,
      ...(hasBody ? { body: Readable.toWeb(req), duplex: "half" } : {}),
    });
    const response = await handler(request);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    console.error(JSON.stringify({ level: "error", event: "route_host_unhandled", errorName: error?.name }));
    res.writeHead(500).end();
  }
}).listen(port, "127.0.0.1", () => {
  console.log(JSON.stringify({ event: "route_host_ready", port, routes: [...routes.keys()] }));
});
