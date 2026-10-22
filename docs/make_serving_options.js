// One sheet: four ways to serve Thetha in real projects, and where the Siyamthanda translator fits.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1000, 44);
sk.text(700, 60, "How a real project can use Thetha", { size: 40, weight: "bold" });
sk.text(700, 102, "the closer the model sits to the microphone, the faster and more private", { size: 24, color: MUTED });

const cards = [
  { x: 60, title: "1 · inside the app", col: CORAL, lines: ["the app loads Thetha", "itself (faster-whisper)"],
    good: ["no internet", "fastest, private"], bad: "needs a PC or laptop", eg: "Siyamthanda hub" },
  { x: 390, title: "2 · laptop API", col: NAVY, lines: ["live.py on a PC,", "devices on the Wi-Fi", "send audio to it"],
    good: ["works today", "$0"], bad: "only on that network", eg: "ESP32 to a hub" },
  { x: 720, title: "3 · cloud API", col: NAVY, lines: ["AWS, with a key;", "any app, anywhere"],
    good: ["phones, websites", "~$0 when idle"], bad: "first call slow (~30 s)", eg: "a phone app" },
  { x: 1050, title: "4 · in the browser", col: NAVY, lines: ["small model runs", "on the visitor's", "phone (today's demo)"],
    good: ["free to host", "private"], bad: "small model only", eg: "the free demo" },
];
for (const c of cards) {
  sk.rect(c.x, 150, 290, 560, { w: c.col === CORAL ? 4 : 2.5, color: c.col });
  sk.text(c.x + 145, 198, c.title, { size: 27, weight: "bold", color: c.col === CORAL ? CORAL : NAVY });
  sk.text(c.x + 145, 262, c.lines, { size: 22, lh: 1.4 });
  sk.line(c.x + 25, 395, c.x + 265, 395, { color: MUTED, w: 1.2 });
  sk.text(c.x + 145, 440, c.good.map(g => "+ " + g), { size: 22, color: EMERALD, lh: 1.4 });
  sk.text(c.x + 145, 540, "- " + c.bad, { size: 20, color: CORAL });
  sk.text(c.x + 145, 650, "e.g. " + c.eg, { size: 21, color: MUTED });
}

// the Siyamthanda pipeline with Thetha dropped in
sk.text(700, 775, "Siyamthanda translator with Thetha inside (option 1)", { size: 28, weight: "bold" });
const steps = [["ESP32 mic", 150], ["Thetha medium", 470, CORAL], ["NLLB translates", 790], ["Piper speaks", 1110]];
for (const [label, x, col] of steps) {
  sk.rect(x - 120, 805, 240, 80, { w: col ? 3.5 : 2.5, color: col || NAVY });
  sk.text(x, 855, label, { size: 23, weight: col ? "bold" : "normal", color: col || NAVY });
}
for (const [a, b] of [[270, 350], [590, 670], [910, 990]]) sk.arrow(a, 845, b, 845, { w: 2.5 });
sk.text(470, 925, ["isiXhosa text, replacing", "Meta Omnilingual"], { size: 19, color: MUTED });
sk.text(950, 925, ["Thetha only listens; it never speaks", "(Swivuriso licence: no voice synthesis)"], { size: 19, color: MUTED });
render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/serving-options.png");
