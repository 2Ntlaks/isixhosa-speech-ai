const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 1000, 33);
sk.text(700, 62, "Stage 2: teach Whisper isiXhosa", { size: 42, weight: "bold" });
sk.text(700, 104, "fine-tune whisper-small on NCHLT, one cloud GPU, ~2-3 hours", { size: 24, color: MUTED });

// row 1: who is used for what
const groups = [
  [60, 400, "Train: 195 speakers", ["~51 h of speech,", "the model learns from these"], NAVY],
  [500, 380, "Dev: 6 speakers", ["checked every 500 steps,", "picks the best checkpoint"], EMERALD],
  [920, 420, "Test: 8 speakers", ["never touched in training,", "the honest final score"], CORAL],
];
groups.forEach(([x, w, t, lines, c]) => {
  sk.rect(x, 150, w, 150, { color: c, w: 3 });
  sk.text(x + w / 2, 195, t, { size: 28, weight: "bold", color: c });
  sk.text(x + w / 2, 238, lines, { size: 22 });
});

// row 2: the training loop
sk.line(60, 345, 1340, 345, { color: MUTED, w: 1.5 });
sk.text(700, 392, "one training step, repeated 4,000 times (~3 passes over the data)", { size: 28, weight: "bold" });
const steps = [
  [70, "1 · Listen", ["32 clips"]],
  [400, "2 · Guess", ["text after the", "<|sw|> tag"]],
  [730, "3 · Compare", ["guess vs true text", "= the loss"]],
  [1060, "4 · Nudge", ["all 244M weights", "a tiny bit"]],
];
steps.forEach(([x, t, lines], i) => {
  sk.rect(x, 430, 270, 140, { w: 3, color: i === 3 ? CORAL : NAVY });
  sk.text(x + 135, 475, t, { size: 28, weight: "bold", color: i === 3 ? CORAL : NAVY });
  sk.text(x + 135, 515, lines, { size: 22 });
  if (i < 3) sk.arrow(x + 276, 500, x + 324, 500);
});
sk.curveArrow(1195, 578, 700, 690, 205, 578, { color: MUTED });
sk.text(700, 668, "repeat", { size: 24, color: MUTED });

// row 3: the two dials and the safety net
sk.line(60, 715, 1340, 715, { color: MUTED, w: 1.5 });
// learning-rate sketch: warm up, then decay
sk.text(330, 760, "Learning rate: how big a nudge", { size: 26, weight: "bold" });
sk.line(110, 920, 560, 920, { color: MUTED, w: 2 });
sk.line(110, 920, 110, 790, { color: MUTED, w: 2 });
sk.line(110, 915, 190, 800, { color: CORAL, w: 3 });
sk.line(190, 800, 550, 912, { color: CORAL, w: 3 });
sk.text(165, 950, "warm up", { size: 20, color: MUTED });
sk.text(400, 950, "then smaller and smaller", { size: 20, color: MUTED });
sk.text(330, 985, "too big: it forgets; too small: it never learns", { size: 20, color: MUTED });

sk.text(1010, 760, "Every 500 steps: a checkpoint", { size: 26, weight: "bold" });
sk.rect(700, 790, 280, 120, { w: 3 });
sk.text(840, 835, "score dev", { size: 26, weight: "bold" });
sk.text(840, 872, "speakers (CER)", { size: 22 });
sk.arrow(986, 850, 1050, 850);
sk.rect(1056, 790, 284, 120, { w: 3, color: EMERALD });
sk.text(1198, 835, "save to S3", { size: 26, weight: "bold", color: EMERALD });
sk.text(1198, 872, "keep the best one", { size: 22 });
sk.text(1020, 955, "if the machine dies, training restarts from here", { size: 20, color: MUTED });

render(sk, require("path").join(__dirname, "stage2.png"));
