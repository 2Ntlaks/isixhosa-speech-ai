const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 900, 21);
sk.text(700, 62, "Stage 1: watch Whisper fail", { size: 42, weight: "bold" });
sk.text(700, 104, "one honest 'before' number, on a cloud GPU, under $1", { size: 24, color: MUTED });

// row 1: what we do
const steps = [
  ["Test clips", ["all 2,770 clips,", "8 unseen speakers"], NAVY],
  ["Whisper-small", ["stock, no training,", "on a cloud GPU"], NAVY],
  ["Compare", ["its guess vs", "the true text"], NAVY],
  ["Baseline", ["WER and CER,", "expect over 80 %"], EMERALD],
];
steps.forEach(([t, lines, c], i) => {
  const x = 60 + i * 340;
  sk.rect(x, 150, 290, 170, { color: c, w: 3 });
  sk.text(x + 145, 200, `${i + 1} · ${t}`, { size: 30, weight: "bold", color: c });
  sk.text(x + 145, 245, lines, { size: 23 });
  if (i < 3) sk.arrow(x + 296, 235, x + 334, 235);
});

// row 2: inside Whisper
sk.line(60, 385, 1340, 385, { color: MUTED, w: 1.5 });
sk.text(700, 435, "inside Whisper: how sound becomes text", { size: 30, weight: "bold" });
// a little waveform
for (let i = 0; i < 14; i++) {
  const x = 60 + i * 10, h = 12 + 50 * Math.abs(Math.sin(i * 0.9)) * (i % 3 ? 1 : 0.5);
  sk.line(x, 560 - h / 2, x, 560 + h / 2, { w: 3 });
}
sk.text(125, 640, "sound", { size: 22, color: MUTED });
const parts = [
  [250, 220, "Log-mel", ["sound drawn", "as a picture"]],
  [545, 240, "Encoder", ["'listens' to", "the picture"]],
  [860, 290, "Decoder", ["writes the text,", "one piece at a time"]],
];
let prev = 205;
parts.forEach(([x, w, t, lines]) => {
  sk.arrow(prev, 560, x - 8, 560);
  sk.rect(x, 480, w, 160, { w: 3, color: t === "Decoder" ? CORAL : NAVY });
  sk.text(x + w / 2, 525, t, { size: 28, weight: "bold", color: t === "Decoder" ? CORAL : NAVY });
  sk.text(x + w / 2, 570, lines, { size: 22 });
  prev = x + w + 8;
});
sk.arrow(prev, 560, 1225, 560);
sk.text(1285, 570, "text", { size: 30, weight: "bold" });

// the catch
sk.curveArrow(860, 745, 900, 700, 960, 648, { color: CORAL });
sk.text(700, 765, "Its first word is always a language tag. isiXhosa has none,", { size: 25, color: CORAL });
sk.text(700, 800, "so it guesses a language it knows and writes in that.", { size: 25, color: CORAL });
sk.text(700, 860, "Your part: listen to about 10 clips next to its guesses, and judge the mistakes.", { size: 23, color: MUTED });

render(sk, require("path").join(__dirname, "stage1.png"));
