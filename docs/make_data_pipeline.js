// One-sheet drawing: the data pipeline that turns four datasets into one clean training list (D-0024).
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1100, 44);
sk.text(700, 62, "The data pipeline: four datasets in, one clean list out", { size: 38, weight: "bold" });

const src = [
  { x: 60, name: "NCHLT", sub: "56 h, reading", c: NAVY },
  { x: 390, name: "FLEURS", sub: "reading, more voices", c: NAVY },
  { x: 720, name: "Swivuriso", sub: "~500 h, new", c: CORAL },
  { x: 1050, name: "NCHLT extra", sub: "~150 h, new", c: CORAL },
];
src.forEach((s, i) => {
  sk.rect(s.x, 110, 290, 105, { w: s.c === CORAL ? 4 : 3, color: s.c });
  sk.text(s.x + 145, 152, s.name, { size: 30, weight: "bold", color: s.c });
  sk.text(s.x + 145, 192, s.sub, { size: 24, color: MUTED });
  sk.arrow(s.x + 145, 222, 330 + i * 250, 288, { w: 2.5 });
});

const steps = [
  ["1. check the sound", "does it play? 1-30 seconds long? has a transcript?"],
  ["2. same writing rules", "lowercase, no punctuation, drop [s] noise tags"],
  ["3. keep the test clean", "drop any training sentence that is also a test sentence"],
  ["4. drop bad clips", "Thetha listens; if audio and words disagree badly, out"],
];
steps.forEach(([h, d], i) => {
  const y = 295 + i * 140;
  sk.rect(200, y, 1000, 100, { w: 3, color: i === 2 ? CORAL : NAVY });
  sk.text(230, y + 42, h, { size: 30, anchor: "start", weight: "bold", color: i === 2 ? CORAL : NAVY });
  sk.text(230, y + 80, d, { size: 24, anchor: "start", color: MUTED });
  if (i < 3) sk.arrow(700, y + 105, 700, y + 135, { w: 2.5 });
});
sk.text(1300, 645, ["test clips", "never get", "in here"], { size: 22, color: CORAL });

sk.arrow(700, 822, 700, 898, { w: 3 });
sk.rect(330, 905, 740, 110, { w: 5, color: EMERALD });
sk.text(700, 950, "one training list + hours per source", { size: 30, weight: "bold", color: EMERALD });
sk.text(700, 990, "saved to S3, ready for training", { size: 24, color: MUTED });

sk.text(700, 1065, "Runs on a cheap cloud machine. Nothing lands on the laptop.", { size: 24, color: MUTED });

render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/data-pipeline.png");
