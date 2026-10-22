// One sheet: R-0032, Thetha as the ears of the Siyamthanda translator. Better hearing, same English: NLLB is the limit.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 960, 32);
sk.text(700, 62, "Thetha inside the Siyamthanda translator (R-0032)", { size: 38, weight: "bold" });
sk.text(700, 104, "100 isiXhosa test clips · the friend's own benchmark · run on a copy", { size: 23, color: MUTED });

// the pipeline
const boxes = [["isiXhosa", "speech", 150, NAVY], ["ears:", "speech -> text", 480, EMERALD], ["NLLB", "text -> English", 810, CORAL], ["Piper", "speaks English", 1140, NAVY]];
for (const [a, b, x, col] of boxes) {
  sk.rect(x - 125, 150, 250, 110, { w: col === NAVY ? 2.5 : 4, color: col });
  sk.text(x, 195, a, { size: 27, weight: "bold", color: col });
  sk.text(x, 235, b, { size: 21, color: MUTED });
}
for (const [a, b] of [[275, 355], [605, 685], [935, 1015]]) sk.arrow(a, 205, b, 205, { w: 2.5 });

// ears panel
sk.rect(330, 300, 300, 330, { w: 2, color: EMERALD });
sk.text(480, 340, "words heard wrong", { size: 24, weight: "bold", color: EMERALD });
sk.text(480, 400, ["Meta (now): 36 %", "Thetha medium: 30 %"], { size: 25, lh: 1.5 });
sk.text(480, 500, ["better on 60 clips,", "worse on 17"], { size: 21, color: MUTED, lh: 1.35 });
sk.text(480, 585, "clearly better ✓", { size: 25, weight: "bold", color: EMERALD });

// translator panel
sk.rect(660, 300, 300, 330, { w: 2, color: CORAL });
sk.text(810, 340, "English quality (BLEU)", { size: 24, weight: "bold", color: CORAL });
sk.text(810, 400, ["with Meta: 18.1", "with Thetha: 18.8"], { size: 25, lh: 1.5 });
sk.text(810, 500, ["even perfect isiXhosa", "text only gets ~19-21"], { size: 21, color: MUTED, lh: 1.35 });
sk.text(810, 585, "the bottleneck", { size: 25, weight: "bold", color: CORAL });

// speed panel
sk.rect(990, 300, 300, 330, { w: 2, color: NAVY });
sk.text(1140, 340, "time to first English", { size: 24, weight: "bold" });
sk.text(1140, 400, ["Meta: 2.1 s", "Thetha medium: 2.7 s"], { size: 25, lh: 1.5 });
sk.text(1140, 500, ["(cloud CPU; the", "laptop is slower)"], { size: 21, color: MUTED, lh: 1.35 });
sk.text(1140, 585, "+0.6 s", { size: 25, weight: "bold" });

// small model aside
sk.rect(40, 300, 260, 330, { w: 1.5, color: MUTED });
sk.text(170, 340, "Thetha small", { size: 24, weight: "bold", color: MUTED });
sk.text(170, 410, ["fastest: 1.6 s", "but 38 % words", "wrong: no use here"], { size: 21, color: MUTED, lh: 1.45 });

// takeaway
sk.text(700, 700, "Thetha gives the translator better ears; the English stays the same until the translator improves", { size: 25, weight: "bold" });
sk.text(700, 760, ["next levers: NLLB 1.3B (the project already supports it) · a test on everyday conversation,",
  "where Thetha should gain most (it learned from 245 h of free isiXhosa speech; this test is read news)"], { size: 22, color: MUTED, lh: 1.5 });
sk.text(700, 880, "Meta's re-run matched the friend's own earlier result exactly (36 % / 6.5 %), so the test setup is faithful", { size: 20, color: MUTED });
render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/siyamthanda-test.png");
