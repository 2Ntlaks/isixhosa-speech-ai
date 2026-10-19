// Images for README.md: banner, progress chart, pipeline. Numbers come from results.md (run IDs in comments).
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const path = require("path");
const out = (f) => path.join(__dirname, f);

// hatch a box with 45-degree pencil strokes (the hand-drawn fill)
function hatch(sk, x, y, w, h, color, gap = 14) {
  for (let k = -h; k < w; k += gap) {
    const x1 = Math.max(x, x + k), y1 = x + k < x ? y + (x - (x + k)) : y;
    const x2 = Math.min(x + w, x + k + h), y2 = y + (x2 - (x + k));
    sk.line(x1, y1 + 0, x2, Math.min(y2, y + h), { color, w: 1.6, jitter: 0.8, passes: 1, opacity: 0.75 });
  }
}

// ---------- 1. banner ----------
{
  const sk = new Sketch(1400, 470, 12);
  sk.text(700, 92, "isiXhosa Speech AI", { size: 64, weight: "bold" });
  sk.text(700, 142, "teaching OpenAI Whisper to hear isiXhosa · ~$10 of cloud GPU", { size: 26, color: MUTED });
  // waveform (speech in)
  const x0 = 90, mid = 300;
  for (let i = 0; i < 44; i++) {
    const x = x0 + i * 9;
    const env = Math.sin((i / 43) * Math.PI) * (0.55 + 0.45 * Math.abs(Math.sin(i * 1.7)));
    const a = 12 + 78 * env;
    sk.line(x, mid - a, x, mid + a, { color: NAVY, w: 3.5, jitter: 1, passes: 1 });
  }
  sk.arrow(520, mid, 610, mid, { color: CORAL, w: 4 });
  // model box
  sk.rect(625, 235, 210, 130, { w: 3.5, color: CORAL });
  sk.text(730, 292, "R-0012", { size: 32, weight: "bold", color: CORAL });
  sk.text(730, 332, "whisper-medium", { size: 22, color: MUTED });
  sk.arrow(850, mid, 930, mid, { color: CORAL, w: 4 });
  // text out (a real FLEURS test sentence, transcribed exactly by R-0012)
  sk.text(945, 275, "isizisele uloliwe imoto", { size: 30, anchor: "start" });
  sk.text(945, 318, "kunye nezinye izixhobo", { size: 30, anchor: "start" });
  sk.text(945, 361, "zothutho", { size: 30, anchor: "start" });
  sk.text(700, 440, "a FLEURS test sentence the model never saw in training, written exactly right", { size: 20, color: MUTED });
  render(sk, out("readme-hero.png"));
}

// ---------- 2. progress chart: CER on FLEURS test (unseen sentences) ----------
{
  const sk = new Sketch(1400, 800, 21);
  sk.text(700, 64, "Letters wrong on unseen isiXhosa sentences", { size: 38, weight: "bold" });
  sk.text(700, 106, "character error rate (CER) on the FLEURS xh_za test set, 1 034 clips · lower is better", { size: 22, color: MUTED });
  const bars = [ // [label lines, CER, run]
    [["stock", "whisper-small"], 65.45, "R-0006"],
    [["stock", "whisper-medium"], 45.86, "R-0011"],
    [["small, trained", "on NCHLT"], 29.81, "R-0005"],
    [["small,", "+ FLEURS"], 10.16, "R-0007"],
    [["medium,", "+ FLEURS"], 8.03, "R-0012"],
  ];
  const left = 150, base = 640, top = 170, bw = 150, step = 236;
  const y = (v) => base - (v / 70) * (base - top);
  for (const t of [0, 20, 40, 60]) { // recessive grid
    sk.line(left - 20, y(t), 1330, y(t), { color: MUTED, w: 1, jitter: 0.6, passes: 1, opacity: 0.35 });
    sk.text(left - 32, y(t) + 8, `${t} %`, { size: 18, color: MUTED, anchor: "end" });
  }
  bars.forEach(([lab, v, run], i) => {
    const x = left + 30 + i * step, c = i === 4 ? CORAL : NAVY;
    hatch(sk, x, y(v), bw, base - y(v), c);
    sk.rect(x, y(v), bw, base - y(v), { color: c, w: 3, jitter: 1.4 });
    sk.text(x + bw / 2, y(v) - 16, `${v.toFixed(1)} %`, { size: 26, weight: "bold", color: i === 4 ? CORAL : NAVY });
    sk.text(x + bw / 2, base + 38, lab, { size: 21 });
    sk.text(x + bw / 2, base + 112, run, { size: 18, color: MUTED });
  });
  sk.line(left - 20, base, 1330, base, { color: NAVY, w: 2.5, jitter: 1 });
  render(sk, out("readme-progress.png"));
}

// ---------- 3. pipeline ----------
{
  const sk = new Sketch(1400, 820, 5);
  sk.text(700, 62, "How a run happens", { size: 40, weight: "bold" });
  sk.text(700, 102, "one machine at a time, each with a hard time cap, each switching itself off", { size: 22, color: MUTED });
  const box = (x, y, w, h, title, lines, c = NAVY) => {
    sk.rect(x, y, w, h, { w: 3, color: c });
    sk.text(x + w / 2, y + 44, title, { size: 26, weight: "bold", color: c });
    sk.text(x + w / 2, y + 84, lines, { size: 20 });
  };
  // row 1: data in
  box(60, 150, 330, 150, "Speech corpora", ["SADiLaR (NCHLT, Soapies)", "Hugging Face (FLEURS)"], MUTED);
  sk.arrow(396, 225, 466, 225);
  box(472, 150, 380, 150, "Downloader", ["small machine, checks", "checksums, then off"]);
  sk.arrow(858, 225, 928, 225);
  box(934, 150, 406, 150, "S3 bucket (private)", ["datasets, models,", "run outputs"], CORAL);
  // row 2: the run
  box(60, 400, 330, 150, "runs/R-xxxx/", ["job.sh + the exact", "git commit"]);
  sk.arrow(396, 475, 466, 475);
  box(472, 400, 380, 150, "GPU machine", ["train, score, upload,", "shut down (max hours)"]);
  sk.curveArrow(960, 308, 880, 330, 800, 392, { color: MUTED, w: 3 }); // data -> GPU
  sk.text(925, 372, "reads data", { size: 18, color: MUTED, anchor: "start" });
  sk.arrow(858, 500, 928, 500);
  box(934, 400, 406, 150, "Results", ["metrics, samples, logs", "back into git"], EMERALD);
  sk.text(700, 600, "every run, even failed ones, gets a row in results.md and a folder in runs/", { size: 20, color: MUTED });
  // row 3: laptop
  sk.line(60, 640, 1340, 640, { color: MUTED, w: 1.5 });
  box(60, 670, 330, 120, "Best model", ["R-0012 from S3"]);
  sk.arrow(396, 730, 466, 730);
  box(472, 670, 380, 120, "8-bit copy", ["4x smaller, same accuracy"]);
  sk.arrow(858, 730, 928, 730);
  box(934, 670, 406, 120, "Thetha on a laptop", ["speak, see the text"], CORAL);
  render(sk, out("readme-pipeline.png"));
}
