const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 1080, 44);
sk.text(700, 62, "Stage 4: isiXhosa with English mixed in", { size: 42, weight: "bold" });
sk.text(700, 104, "no recording needed: open data to learn from, TV soap operas to test on", { size: 24, color: MUTED });

// row 1: who is used for what (D-0016)
const groups = [
  [60, 400, "Train: open data only", ["NCHLT isiXhosa + FLEURS", "+ NCHLT English (new)"], NAVY],
  [500, 380, "Dev: Soapies, 38 voices", ["picks the best checkpoint,", "never learned from"], EMERALD],
  [920, 420, "Test: Soapies, 5 voices", ["391 real mixed clips from", "Generations, Rhythm City"], CORAL],
];
groups.forEach(([x, w, t, lines, c]) => {
  sk.rect(x, 150, w, 150, { color: c, w: 3 });
  sk.text(x + w / 2, 195, t, { size: 28, weight: "bold", color: c });
  sk.text(x + w / 2, 238, lines, { size: 22 });
});
sk.text(1130, 330, "research-only licence: scoring only (D-0016)", { size: 19, color: MUTED });

// row 2: where R-0012 stands today (R-0014)
sk.line(60, 360, 1340, 360, { color: MUTED, w: 1.5 });
sk.text(700, 405, "Today (R-0014): R-0012 hears English, then spells it like isiXhosa", { size: 28, weight: "bold" });
const ex = [ // single words only: Soapies transcripts are research-only (D-0016, D-0019)
  [470, "stubborn", "istabhunga"],
  [530, "biological", "ngephological"],
  [590, "i party", "ipathi"],
];
sk.text(110, 440, "said (English)", { size: 20, color: MUTED, anchor: "start" });
sk.text(480, 440, "wrote", { size: 20, color: MUTED, anchor: "start" });
ex.forEach(([y, said, wrote]) => {
  sk.text(110, y + 12, said, { size: 28, color: NAVY, anchor: "start" });
  sk.arrow(330, y + 2, 440, y + 2, { color: MUTED, w: 2.5 });
  sk.text(480, y + 12, wrote, { size: 28, color: CORAL, anchor: "start" });
});
sk.rect(860, 430, 480, 190, { w: 3 });
sk.text(1100, 470, "letters wrong: 38 %", { size: 28, weight: "bold", color: CORAL });
sk.text(1100, 505, "(8 % on FLEURS read speech)", { size: 20, color: MUTED });
sk.text(1100, 552, "English words right: 32 %", { size: 24 });
sk.text(1100, 592, "isiXhosa words right: 15 %", { size: 24 });

// row 3: the two November runs
sk.line(60, 660, 1340, 660, { color: MUTED, w: 1.5 });
sk.text(700, 705, "November: two runs from R-0012, one change each (~$5-6 together)", { size: 28, weight: "bold" });
sk.rect(60, 740, 400, 150, { w: 3 });
sk.text(260, 785, "R-0015", { size: 28, weight: "bold" });
sk.text(260, 828, ["+ 10 h South African", "English, <|en|> tag"], { size: 22 });
sk.arrow(466, 815, 524, 815);
sk.rect(530, 740, 810, 150, { w: 3, color: CORAL });
sk.text(680, 785, "R-0016", { size: 28, weight: "bold", color: CORAL });
sk.text(680, 828, ["+ 8000 stitched", "clips"], { size: 22 });
// a stitched clip: three audio pieces joined with short silences
const pieces = [[830, 150, "isiXhosa", NAVY], [1000, 130, "English", CORAL], [1150, 150, "isiXhosa", NAVY]];
pieces.forEach(([x, w, t, c]) => {
  sk.rect(x, 772, w, 50, { w: 2.5, color: c });
  sk.text(x + w / 2, 805, t, { size: 20, color: c });
});
sk.text(990, 797, "·", { size: 24, color: MUTED });
sk.text(1140, 797, "·", { size: 24, color: MUTED });
sk.text(1065, 860, "real clips joined: one clip, both languages", { size: 20, color: MUTED });

sk.text(700, 945, "Pass mark: Soapies test better, NCHLT and FLEURS test not much worse", { size: 24, weight: "bold", color: EMERALD });
sk.text(700, 990, "if it works: a few of your own recordings as the final check (optional)", { size: 22, color: MUTED });
sk.text(700, 1030, "limit: real switches happen inside words (i-grapefruit); stitching only switches between phrases", { size: 19, color: MUTED });

render(sk, require("path").join(__dirname, "stage4.png"));
