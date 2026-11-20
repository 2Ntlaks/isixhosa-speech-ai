// Drives Chrome or Edge through the R-0038 browser test and samples the browser's memory.
//   node bench.mjs chrome|edge [headless|window] [repeats]
import puppeteer from "puppeteer-core"; import { exec } from "node:child_process"; import fs from "node:fs";
const [browserName = "chrome", mode = "headless", repeats = "5", model = "R-0035"] = process.argv.slice(2);
const EXE = { chrome: "C:/Program Files/Google/Chrome/Application/chrome.exe",
              edge: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" }[browserName];
const PROFILE = `C:/Users/ntlak/isixhosa-speech-ai-data/webtest/profile-${browserName}`;  // model arg read below
const CLIPS = [{ id: "fleurs_16251693488553696524", max_new_tokens: 225 }, { id: "nchlt_xho_500m_0267", max_new_tokens: 96 },
               { id: "fleurs_14186816915482707666", max_new_tokens: 225 }, { id: "silence5", max_new_tokens: 225 }];
const tag = PROFILE.split("/").pop();
let peak = { total_mb: 0, gpu_mb: 0, renderer_mb: 0 }, sampling = true;
function sample() {  // private bytes of every process of this browser profile
  const ps = `Get-CimInstance Win32_Process -Filter "Name like '%${browserName === "edge" ? "msedge" : "chrome"}%'" | ? { $_.CommandLine -like '*${tag}*' } | % { '{0}|{1}' -f $_.PrivatePageCount, ($_.CommandLine -match '--type=(\S+)' | % { $matches[1] }) }`;
  exec(`powershell -NoProfile -Command "${ps.replace(/"/g, '\\"')}"`, (e, out) => {
    if (!e) {
      let total = 0, gpu = 0, rend = 0;
      for (const line of out.trim().split(/\r?\n/)) { const [b, t] = line.split("|"); const mb = +b / 1e6; total += mb; if (t === "gpu-process") gpu += mb; if (t === "renderer") rend += mb; }
      peak = { total_mb: Math.max(peak.total_mb, total), gpu_mb: Math.max(peak.gpu_mb, gpu), renderer_mb: Math.max(peak.renderer_mb, rend) };
    }
    if (sampling) setTimeout(sample, 1000);
  });
}
const browser = await puppeteer.launch({ executablePath: EXE, headless: mode === "headless", userDataDir: PROFILE,
  args: ["--no-first-run", "--no-default-browser-check", "--enable-unsafe-webgpu"], protocolTimeout: 1800000 });
sample();
const page = await browser.newPage();
page.on("console", m => console.log("[page]", m.text()));
const result = {};
for (const pass of ["first", "second"]) {  // second = page reloaded, browser cache warm
  await page.goto("http://127.0.0.1:8765/", { waitUntil: "load" });
  await page.waitForFunction(() => typeof window.bench === "function");
  const t = Date.now();
  result[pass] = await page.evaluate(o => window.bench(o), { clips: pass === "first" ? CLIPS.slice(0, 1) : CLIPS, repeats: pass === "first" ? 1 : +repeats, dtype: "q4f16", device: "webgpu", model });
  result[pass].wall_s = (Date.now() - t) / 1000;
  console.log(pass, "load", result[pass].load_s.toFixed(1), "s, warm-up", result[pass].warmup_s.toFixed(1), "s");
}
sampling = false;
result.browser = browserName; result.mode = mode; result.version = await browser.version(); result.peak_memory = peak;
await browser.close();
fs.writeFileSync(`result-${browserName}-${mode}-${model}.json`, JSON.stringify(result, null, 1));
console.log(JSON.stringify({ adapter: result.second.adapter, peak }, null, 1));
