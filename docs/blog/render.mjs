// Export .excalidraw files to PNG with real Excalidraw (0.18, Excalifont), in headless Chrome.
//   node docs/blog/render.mjs <puppeteer-core dir> <out dir> a.excalidraw b.excalidraw ...
import { createRequire } from "module";
import fs from "fs";
import path from "path";
const [, , pupDir, outDir, ...files] = process.argv;
const puppeteer = createRequire(path.join(pupDir, "package.json"))("puppeteer-core");
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const page = await browser.newPage();
page.on("pageerror", (e) => console.log("[page error]", e.message));
await page.setContent(`<html><body><script>window.EXCALIDRAW_ASSET_PATH='https://esm.sh/@excalidraw/excalidraw@0.18.0/dist/prod/';</script>
<script type="module">import * as X from 'https://esm.sh/@excalidraw/excalidraw@0.18.0?bundle-deps'; window.X = X; window.ready = true;</script></body></html>`);
await page.waitForFunction("window.ready === true", { timeout: 180000 });
for (const f of files) {
  const scene = JSON.parse(fs.readFileSync(f, "utf8"));
  const b64 = await page.evaluate(async (scene) => {
    const blob = await window.X.exportToBlob({ elements: scene.elements, appState: { ...scene.appState, exportBackground: true, exportWithDarkMode: false },
      files: scene.files || {}, mimeType: "image/png", exportPadding: 0, getDimensions: (w, h) => ({ width: w * 2, height: h * 2, scale: 2 }) });
    const buf = new Uint8Array(await blob.arrayBuffer()); let s = ""; for (const c of buf) s += String.fromCharCode(c); return btoa(s);
  }, scene);
  const out = path.join(outDir, path.basename(f).replace(/\.excalidraw$/, ".png"));
  fs.writeFileSync(out, Buffer.from(b64, "base64"));
  console.log("wrote", out);
}
await browser.close();
