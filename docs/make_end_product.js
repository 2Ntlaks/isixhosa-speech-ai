// Sketch of the finished project: demo page, Hugging Face model page, write-up. node docs/make_end_product.js
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account3/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 900, 5);
sk.text(700, 60, "What you end up with", { size: 42, weight: "bold" });
sk.text(700, 102, "three things anyone can open in a browser", { size: 24, color: MUTED });

// panel 1: the demo
let x = 50, y = 150, w = 410, h = 560;
sk.rect(x, y, w, h, { w: 3 });
sk.line(x, y + 44, x + w, y + 44, { w: 2 });
[0, 1, 2].forEach(i => sk.ellipse(x + 24 + i * 22, y + 22, 7, 7, { w: 2 }));
sk.text(x + w / 2, y + 92, "1  The demo", { size: 30, weight: "bold", color: CORAL });
sk.ellipse(x + w / 2, y + 185, 52, 52, { color: CORAL, w: 4 });
sk.rect(x + w / 2 - 12, y + 160, 24, 38, { color: CORAL, w: 3 });
sk.line(x + w / 2, y + 205, x + w / 2, y + 220, { color: CORAL, w: 3 });
sk.text(x + w / 2, y + 278, "press, speak isiXhosa", { size: 22 });
sk.rect(x + 34, y + 310, w - 68, 150, { color: MUTED, w: 2 });
sk.textLines(x + 56, y + 345, [250, 300, 210], 34, NAVY);
sk.text(x + w / 2, y + 500, ["transcript appears", "in a few seconds"], { size: 22, color: MUTED });

// panel 2: Hugging Face model page
x = 495; sk.rect(x, y, w, h, { w: 3 });
sk.line(x, y + 44, x + w, y + 44, { w: 2 });
sk.text(x + w / 2, y + 92, "2  Your model", { size: 30, weight: "bold", color: CORAL });
sk.text(x + w / 2, y + 140, "huggingface.co/ntlaks/...", { size: 21, color: MUTED });
sk.text(x + 40, y + 200, "word errors (lower is better)", { size: 21, anchor: "start" });
const bars = [["Whisper as-is", 330, MUTED], ["after stage 2", 170, NAVY], ["your best", 110, EMERALD]];
bars.forEach(([lab, len, c], i) => {
  const by = y + 240 + i * 70;
  sk.text(x + 40, by + 26, lab, { size: 20, anchor: "start", color: c });
  sk.rect(x + 40, by + 36, len, 18, { color: c, w: 3 });
});
sk.text(x + w / 2, y + 480, ["model card: data, scores,", "limits, licence credit"], { size: 21, color: MUTED });

// panel 3: write-up
x = 940; sk.rect(x, y, w, h, { w: 3 });
sk.line(x, y + 44, x + w, y + 44, { w: 2 });
sk.text(x + w / 2, y + 92, "3  The story", { size: 30, weight: "bold", color: CORAL });
sk.text(x + w / 2, y + 140, "ntlaks.dev/writing/...", { size: 21, color: MUTED });
sk.text(x + 36, y + 196, "Teaching Whisper isiXhosa", { size: 22, weight: "bold", anchor: "start" });
sk.textLines(x + 36, y + 232, [330, 300, 320], 28, MUTED);
sk.rect(x + 36, y + 330, w - 72, 120, { color: NAVY, w: 2 });
sk.text(x + w / 2, y + 398, "architecture drawing", { size: 20, color: NAVY });
sk.text(x + w / 2, y + 500, ["what you built, what failed,", "what it cost"], { size: 21, color: MUTED });

sk.text(700, 790, "+ the project folder: code, results.md, decisions.md, drawings", { size: 24, color: NAVY });
sk.text(700, 840, "bar lengths are placeholders; real numbers come from stages 1 to 3", { size: 20, color: MUTED });
render(sk, require("path").join(__dirname, "end-product.png"));
