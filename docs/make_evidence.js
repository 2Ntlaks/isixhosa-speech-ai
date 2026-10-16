// Where evidence lives and how it becomes the write-up. node docs/make_evidence.js
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account3/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 900, 9);
sk.text(700, 60, "The evidence trail", { size: 42, weight: "bold" });
sk.text(700, 102, "agents record as they work, so the story writes itself later", { size: 24, color: MUTED });

// left: what happens
const ev = [["a training run", 240], ["an error", 380], ["a choice you make", 520], ["end of a session", 660]];
sk.text(200, 160, "what happens", { size: 26, color: MUTED });
ev.forEach(([t, y]) => { sk.rect(60, y - 40, 280, 76, { w: 2.5 }); sk.text(200, y + 8, t, { size: 26 }); });

// middle: files
const files = [["runs/R-0001/", "+ results.md row", 240], ["problems.md", "exact error, cause, fix", 380],
               ["decisions.md", "options, your call, why", 520], ["JOURNAL.md", "done, cost, next step", 660]];
files.forEach(([f, d, y]) => {
  sk.arrow(352, y, 488, y, { w: 2.5 });
  sk.rect(500, y - 48, 380, 96, { color: EMERALD, w: 3 });
  sk.text(690, y - 6, f, { size: 28, weight: "bold", color: EMERALD });
  sk.text(690, y + 28, d, { size: 21, color: NAVY });
});
sk.text(690, 160, "the source of truth (in git)", { size: 26, color: MUTED });

// right: outputs
sk.rect(1010, 300, 330, 300, { color: CORAL, w: 4 });
sk.text(1175, 360, "the write-up", { size: 32, weight: "bold", color: CORAL });
sk.text(1175, 410, ["every number cites", "a run ID", "", "what failed and why", "", "what it cost"], { size: 22, lh: 1.3 });
[240, 380, 520, 660].forEach(y => sk.arrow(892, y, 1000, 450 + (y - 450) * 0.35, { color: CORAL, w: 2 }));
sk.text(1175, 670, ["+ interviews", "+ model card"], { size: 22, color: MUTED, lh: 1.4 });

sk.text(700, 800, "append-only: mistakes stay in the record, corrections are new entries", { size: 23, color: NAVY });
sk.text(700, 845, "big files (audio, checkpoints, huge logs) live in S3; the run folder records where", { size: 20, color: MUTED });
render(sk, require("path").join(__dirname, "evidence.png"));
