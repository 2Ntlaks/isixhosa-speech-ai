const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account3/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 960, 11);
sk.text(700, 62, "Teach an AI to hear isiXhosa", { size: 42, weight: "bold" });
sk.text(700, 104, "fine-tune Whisper on South African speech, on your AWS credits", { size: 24, color: MUTED });

// row 1: the pipeline
const bx = [60, 400, 740, 1080], by = 160, bw = 260, bh = 180;
const boxes = [
  ["Speech data", ["NCHLT: 56 h", "+ Google FLEURS"], NAVY],
  ["Whisper", ["99 languages,", "but no isiXhosa"], NAVY],
  ["Fine-tune", ["AWS spot GPU", "about $20"], CORAL],
  ["Your model", ["on Hugging Face", "+ live demo"], EMERALD],
];
boxes.forEach(([t, lines, c], i) => {
  sk.rect(bx[i], by, bw, bh, { color: c, w: i === 2 ? 4 : 3 });
  sk.text(bx[i] + bw / 2, by + 52, t, { size: 32, weight: "bold", color: c });
  sk.text(bx[i] + bw / 2, by + 102, lines, { size: 24, color: NAVY, lh: 1.4 });
  if (i < 3) sk.arrow(bx[i] + bw + 12, by + bh / 2, bx[i + 1] - 12, by + bh / 2, { w: 3 });
});
sk.curveArrow(1210, by + bh + 14, 1040, by + bh + 85, 870, by + bh + 14, { color: CORAL, w: 3 });
sk.text(1040, by + bh + 82, "measure errors (WER), repeat", { size: 22, color: CORAL });

// row 2: five stages
sk.line(60, 475, 1340, 475, { color: MUTED, w: 2 });
sk.text(700, 525, "5 stages, and what you learn in each", { size: 30, weight: "bold" });
const sx = [60, 325, 590, 855, 1120], sy = 560, sw = 230, sh = 330;
const stages = [
  ["1 Baseline", ["test Whisper as-is", "(expect it to fail)"], ["audio as images", "error rate (WER)"]],
  ["2 First train", ["whisper-small", "on NCHLT"], ["training loop", "learning rate"]],
  ["3 Improve", ["clean the text", "bigger model"], ["experiments", "overfitting"]],
  ["4 Your niche", ["isiXhosa + English", "mixed, your voice"], ["new data", "real-world use"]],
  ["5 Ship it", ["Hugging Face", "+ demo page"], ["deploy", "write it up"]],
];
stages.forEach(([t, what, learn], i) => {
  const c = i === 3 ? CORAL : NAVY;
  sk.rect(sx[i], sy, sw, sh, { color: c, w: i === 3 ? 4 : 2.5 });
  sk.text(sx[i] + sw / 2, sy + 48, t, { size: 28, weight: "bold", color: c });
  sk.text(sx[i] + sw / 2, sy + 100, what, { size: 21, color: NAVY, lh: 1.4 });
  sk.line(sx[i] + 30, sy + 178, sx[i] + sw - 30, sy + 178, { color: MUTED, w: 1.5 });
  sk.text(sx[i] + sw / 2, sy + 215, "you learn:", { size: 19, color: MUTED });
  sk.text(sx[i] + sw / 2, sy + 252, learn, { size: 21, color: EMERALD, lh: 1.4 });
  if (i < 4) sk.arrow(sx[i] + sw + 4, sy + sh / 2, sx[i + 1] - 4, sy + sh / 2, { w: 2 });
});
sk.text(700, 935, "total GPU spend about $15-30 of your ~$133 credits", { size: 22, color: MUTED });
render(sk, require("path").join(__dirname, "roadmap.png"));
