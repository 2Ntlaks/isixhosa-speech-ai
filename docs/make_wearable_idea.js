// One-sheet drawing: how a wearable isiXhosa translator would work (idea, not a plan).
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1040, 21);
sk.text(700, 70, "A wearable isiXhosa translator: how it would work", { size: 40, weight: "bold" });

// the four steps
const steps = [
  { x: 60, head: "1. hear", body: ["mic badge", "on your shirt"], note: "your degree", c: NAVY },
  { x: 400, head: "2. write it", body: ["Thetha", "(your model)"], note: "already built", c: CORAL },
  { x: 740, head: "3. translate", body: ["isiXhosa", "to English"], note: "free models exist", c: NAVY },
  { x: 1080, head: "4. speak", body: ["voice in", "your earbud"], note: "free voices exist", c: NAVY },
];
for (const s of steps) {
  sk.rect(s.x, 160, 260, 200, { w: s.c === CORAL ? 5 : 3, color: s.c });
  sk.text(s.x + 130, 220, s.head, { size: 32, weight: "bold", color: s.c });
  sk.text(s.x + 130, 275, s.body, { size: 26 });
  sk.text(s.x + 130, 410, s.note, { size: 24, color: s.c === CORAL ? CORAL : MUTED });
}
for (const x of [325, 665, 1005]) sk.arrow(x, 260, x + 70, 260, { w: 3 });

sk.line(60, 470, 1340, 470, { color: MUTED, w: 2 });

// where the thinking runs
sk.text(370, 530, "Where does the thinking run?", { size: 34, weight: "bold" });
sk.rect(60, 570, 620, 150, { w: 4, color: CORAL });
sk.text(80, 615, "A. badge sends sound to", { size: 28, anchor: "start", weight: "bold" });
sk.text(80, 655, "your phone or a server", { size: 28, anchor: "start", weight: "bold" });
sk.text(80, 700, "quick to build (your API idea)", { size: 24, anchor: "start", color: CORAL });
sk.text(600, 650, "start", { size: 26, color: EMERALD, weight: "bold" });
sk.text(600, 685, "here", { size: 26, color: EMERALD, weight: "bold" });

sk.rect(60, 750, 620, 150, { w: 3 });
sk.text(80, 795, "B. everything on the badge", { size: 28, anchor: "start", weight: "bold" });
sk.text(80, 840, "too slow today: your laptop took", { size: 24, anchor: "start", color: MUTED });
sk.text(80, 875, "6-7 s per clip (R-0013)", { size: 24, anchor: "start", color: MUTED });

// the real hard parts
sk.text(1040, 530, "The real hard parts", { size: 34, weight: "bold" });
const hard = [
  ["noisy streets", "it learned from quiet reading"],
  ["delay", "each sentence takes seconds"],
  ["mistakes stack up", "wrong word, wrong translation"],
  ["people mix in English", "TV test: CER 38 % (R-0014)"],
];
hard.forEach(([a, b], i) => {
  const y = 595 + i * 80;
  sk.text(760, y, "- " + a, { size: 28, anchor: "start", color: i === 3 ? CORAL : NAVY });
  sk.text(790, y + 32, b, { size: 22, anchor: "start", color: MUTED });
});

sk.text(700, 950, "Data isn't the blocker for a first version.", { size: 28, color: CORAL, weight: "bold" });
sk.text(700, 990, "Real conversation data is the blocker for a good one.", { size: 26, color: MUTED });

render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/wearable-idea.png");
