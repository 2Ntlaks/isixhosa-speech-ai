// Local server for the R-0038 browser test: COOP/COEP like the demo Space, model files served from where they already are.
import { fileURLToPath } from "node:url"; import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = "C:/Users/ntlak/isixhosa-speech-ai-data", REPO = "C:/Users/ntlak/OneDrive/Documents/isixhosa-speech-ai";
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
  ".wasm": "application/wasm", ".onnx": "application/octet-stream", ".wav": "audio/wav" };
function resolve(u) {
  let m;
  if ((m = u.match(/^\/models\/R-0035\/onnx\/([\w.]+\.onnx)$/))) return `${DATA}/onnx/R-0035/${m[1]}`;
  if ((m = u.match(/^\/models\/oc-medium\/((?:onnx\/)?[\w.]+)$/))) return `${DATA}/onnx/oc-medium/${m[1]}`;  // onnx-community stock medium, speed reference
  if (u === "/models/R-0035/tokenizer.json") return `${DATA}/models/R-0035-int8/tokenizer.json`;
  if ((m = u.match(/^\/models\/R-0035\/([\w.]+\.json)$/))) return `${DATA}/onnx/R-0035/${m[1]}`;
  if ((m = u.match(/^\/audio\/(fleurs_(\d+))\.wav$/))) return `${REPO}/data/fleurs_xh_za/audio/test/${m[2]}.wav`;
  if ((m = u.match(/^\/audio\/(nchlt_xho_(\d{3})\w_\d+)\.wav$/))) return `${REPO}/data/nchlt_xho/audio/${m[2]}/${m[1]}.wav`;
  const p = path.join(HERE, decodeURIComponent(u));
  return p.startsWith(HERE) ? p : null;
}
http.createServer((req, res) => {
  const u = req.url.split("?")[0], f = resolve(u === "/" ? "/index.html" : u);
  const h = { "Cross-Origin-Opener-Policy": "same-origin", "Cross-Origin-Embedder-Policy": "require-corp",
              "Cross-Origin-Resource-Policy": "cross-origin", "Cache-Control": "no-cache" };
  if (!f || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404, h); return res.end("not found"); }
  res.writeHead(200, { ...h, "Content-Type": TYPES[path.extname(f)] || "application/octet-stream", "Content-Length": fs.statSync(f).size });
  fs.createReadStream(f).pipe(res);
}).listen(8765, "127.0.0.1", () => console.log("http://127.0.0.1:8765"));
