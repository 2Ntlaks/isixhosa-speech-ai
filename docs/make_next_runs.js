// One-sheet drawing: the three runs of D-0031 (R-0033, R-0034, R-0035), one question each, before they run.
//   node docs/make_next_runs.js  ->  docs/next-runs.png
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1560, 35);
sk.text(700, 66, "Three runs, one question each", { size: 40, weight: "bold" });
sk.text(700, 112, "R-0033 to R-0035, planned November 2026 (D-0031)", { size: 24, color: MUTED });

// ---- R-0033: measure fairly first --------------------------------------------------------------
let y = 160;
sk.rect(50, y, 1300, 400, { w: 3 });
sk.text(80, y + 50, "R-0033  How good is R-0019 if it can't get stuck?", { size: 31, weight: "bold", anchor: "start" });
sk.text(80, y + 92, "(scoring only, no training)", { size: 22, color: MUTED, anchor: "start" });
sk.rect(90, y + 150, 200, 110, { w: 3, color: MUTED });
sk.text(190, y + 195, ["model writes", "the text"], { size: 25 });
sk.arrow(300, y + 205, 400, y + 205, { w: 3 });
sk.rect(410, y + 140, 330, 130, { w: 4, color: CORAL });
sk.text(575, y + 185, ["does it repeat", "itself? (zip test)"], { size: 26, color: CORAL, weight: "bold" });
sk.arrow(750, y + 180, 880, y + 160, { w: 3, color: EMERALD });
sk.text(815, y + 140, "no", { size: 24, color: EMERALD });
sk.text(1010, y + 165, "keep it", { size: 28, color: EMERALD, weight: "bold" });
sk.arrow(750, y + 235, 880, y + 265, { w: 3, color: CORAL });
sk.text(815, y + 290, "yes", { size: 24, color: CORAL });
sk.text(1105, y + 255, ["write it again with a little", "randomness (0.2, 0.4, 0.6)"], { size: 24 });
sk.curveArrow(1060, y + 300, 760, y + 370, 575, y + 280, { w: 2, color: MUTED });
sk.text(200, y + 340, ["the 901-letter runaway", "that sank R-0029"], { size: 22, color: MUTED });
sk.text(1030, y + 365, "~$2 with R-0034", { size: 22, color: MUTED });

// ---- R-0034: is Meta's free model already as good? ---------------------------------------------
y = 600;
sk.rect(50, y, 1300, 400, { w: 3 });
sk.text(80, y + 50, "R-0034  Is Meta's free model already as good?", { size: 31, weight: "bold", anchor: "start" });
sk.rect(90, y + 90, 560, 170, { w: 3, color: NAVY });
sk.text(370, y + 130, "Thetha (Whisper)", { size: 28, weight: "bold" });
sk.text(370, y + 180, ["always listens to 30 s,", "writes word by word: can loop"], { size: 23, color: MUTED });
sk.rect(750, y + 90, 560, 170, { w: 3, color: NAVY });
sk.text(1030, y + 130, "Meta Omnilingual CTC", { size: 28, weight: "bold" });
sk.text(1030, y + 180, ["reads every 20 ms slice at once:", "fast on a CPU, never loops"], { size: 23, color: MUTED });
sk.text(700, y + 180, "vs", { size: 30, weight: "bold" });
sk.text(90, y + 310, "fair tests:", { size: 25, weight: "bold", color: EMERALD, anchor: "start" });
sk.text(240, y + 310, "FLEURS, Soapies (mixed speech)", { size: 25, anchor: "start" });
sk.text(90, y + 355, "not fair:", { size: 25, weight: "bold", color: CORAL, anchor: "start" });
sk.text(240, y + 355, "Swivuriso read prompts, NCHLT (one side trained on them)", { size: 25, anchor: "start" });

// ---- R-0035: train the medium model properly ---------------------------------------------------
y = 1040;
sk.rect(50, y, 1300, 480, { w: 3 });
sk.text(80, y + 50, "R-0035  Train the medium model properly", { size: 31, weight: "bold", anchor: "start" });
sk.text(80, y + 92, "same 310 h as R-0029, four fixes, ~6 h, ~$12-13", { size: 22, color: MUTED, anchor: "start" });
const fixes = [
  ["2.9 passes over", "the data, not 1.3"],
  ["best checkpoint chosen", "on Swivuriso + FLEURS"],
  ["SpecAugment: hide", "bits of the sound"],
  ["dev sentences not", "cut off at 96 tokens"],
];
fixes.forEach((f, i) => {
  const x = 70 + i * 315;
  sk.rect(x, y + 125, 300, 130, { w: 3, color: NAVY });
  sk.text(x + 150, y + 175, f, { size: 22 });
});
sk.rect(200, y + 300, 1000, 150, { w: 5, color: CORAL });
sk.text(700, y + 345, "ships only if, scored the same way as R-0019:", { size: 26, weight: "bold", color: CORAL });
sk.text(700, y + 395, ["fewer letter errors on Swivuriso AND FLEURS,", "NCHLT no more than 0.5 worse"], { size: 25 });

render(sk, __dirname + "/next-runs.png");
