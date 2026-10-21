// One-sheet drawing: R-0019 (more data) vs R-0012 (today's Thetha), letters wrong per 100, four tests.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1000, 55);
sk.text(700, 62, "More data made Thetha better at real speech", { size: 40, weight: "bold" });
sk.text(700, 108, "letters wrong out of every 100 (lower is better)", { size: 26, color: MUTED });

const rows = [
  ["people talking freely", "Swivuriso test, unscripted", 10.8, 4.1, "-62 %"],
  ["people reading", "Swivuriso test, scripted", 7.6, 4.1, "-46 %"],
  ["sentences it never heard", "FLEURS test (held-out split)", 8.03, 6.24, "-22 %"],
  ["the old reading test", "NCHLT test", 2.33, 2.31, "same"],
];
const x0 = 560, scale = 50;   // 1 letter per 100 = 50 px
rows.forEach(([name, sub, before, after, change], i) => {
  const y = 175 + i * 165;
  sk.text(80, y + 30, name, { size: 30, anchor: "start", weight: "bold" });
  sk.text(80, y + 68, sub, { size: 22, anchor: "start", color: MUTED });
  sk.rect(x0, y, before * scale, 42, { color: MUTED, w: 3 });
  sk.text(x0 + before * scale + 20, y + 30, `${before}  before`, { size: 24, anchor: "start", color: MUTED });
  sk.rect(x0, y + 58, after * scale, 42, { color: EMERALD, w: 4 });
  sk.text(x0 + after * scale + 20, y + 88, `${after}  now`, { size: 26, anchor: "start", color: EMERALD, weight: "bold" });
  sk.text(x0 + after * scale + 175, y + 88, change, { size: 30, anchor: "start", color: CORAL, weight: "bold" });
});

sk.line(60, 840, 1340, 840, { color: MUTED, w: 2 });
sk.text(700, 890, "before = R-0012 (today's Thetha) · now = R-0019 (+146 h of Swivuriso, one change)", { size: 24, color: MUTED });
sk.text(700, 935, "~3 hours on one cloud GPU, about $5.50 of credits", { size: 24, color: MUTED });
render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/r0019-results.png");
