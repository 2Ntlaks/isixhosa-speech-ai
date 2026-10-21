// One-sheet drawing: where more isiXhosa speech could come from, matched to what Thetha is weak at.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1180, 33);
sk.text(700, 70, "Where more isiXhosa speech could come from", { size: 40, weight: "bold" });
sk.text(330, 140, "Thetha is weak at...", { size: 30, color: MUTED });
sk.text(990, 140, "...what would fix it", { size: 30, color: MUTED });

const rows = [
  { weak: ["only ~56 h of", "people reading"], src: "Swivuriso (African Next Voices)",
    note: ["~500 h of isiXhosa, read AND unscripted", "free, CC BY 4.0, accept terms on Hugging Face"], c: CORAL, tag: "biggest win" },
  { weak: ["not many", "different voices"], src: "NCHLT auxiliary recordings",
    note: ["~150 h more from the same campaign,", "left out of the official release (CC BY 3.0)"], c: NAVY },
  { weak: ["quiet rooms", "only"], src: "add noise to clips you have",
    note: ["street, taxi, crowd sounds mixed in", "during training; no new speech needed"], c: NAVY, tag: "costs nothing" },
  { weak: ["people mixing", "in English"], src: "your voice + friends (written OK)",
    note: ["record real mixed sentences; keep", "the TV clips as the test only"], c: NAVY },
];
rows.forEach((r, i) => {
  const y = 180 + i * 190;
  sk.rect(60, y, 420, 150, { w: 3, color: MUTED });
  sk.text(270, y + 62, r.weak, { size: 28 });
  sk.arrow(495, y + 75, 600, y + 75, { w: 3 });
  sk.rect(620, y, 720, 150, { w: r.c === CORAL ? 5 : 3, color: r.c });
  sk.text(645, y + 48, r.src, { size: 30, anchor: "start", weight: "bold", color: r.c });
  sk.text(645, y + 92, r.note, { size: 23, anchor: "start", color: MUTED });
  if (r.tag) sk.text(1245, y + 48, r.tag, { size: 24, color: r.c === CORAL ? CORAL : EMERALD, weight: "bold" });
});

const y0 = 960;
sk.line(60, y0, 1340, y0, { color: MUTED, w: 2 });
sk.text(700, y0 + 50, "Dead ends", { size: 30, weight: "bold", color: MUTED });
sk.text(700, y0 + 95, "Common Voice isiXhosa: 30 clips  ·  Google WAXAL: no isiXhosa", { size: 25, color: MUTED });
sk.text(700, y0 + 135, "radio / YouTube: no permission to train on it", { size: 25, color: MUTED });

render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/more-data.png");
