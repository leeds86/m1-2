import { mkdir, copyFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const configured = process.env.API_BASE_URL;
if (!configured) throw new Error("Set API_BASE_URL to the Render backend origin before building.");
const url = new URL(configured);
if (!["https:", "http:"].includes(url.protocol) || url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
  throw new Error("API_BASE_URL must be an HTTP(S) origin without credentials, path or query.");
}
if (process.env.VERCEL && url.protocol !== "https:") throw new Error("Vercel deployments require an HTTPS backend.");
const output = path.join(root, "dist");
await mkdir(output, { recursive: true });
for (const name of ["index.html", "styles.css", "app.js", "favicon.svg"]) await copyFile(path.join(root, name), path.join(output, name));
await writeFile(path.join(output, "config.js"), `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: url.origin })};\n`);
console.log("Built frontend/dist. Only the public API origin is included.");
