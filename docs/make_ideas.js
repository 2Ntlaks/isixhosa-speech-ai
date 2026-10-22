// One sheet: realistic but ambitious next directions for Thetha, with the agent's pick marked.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 980, 41);
sk.text(700, 62, "Where Thetha could go next", { size: 40, weight: "bold" });
sk.text(700, 106, "today: 3 models · free demo · 245 h of everyday speech · fewer errors than Meta 1B on read news (one test)", { size: 23, color: MUTED });

const cards = [
  // x, y, title, lines, cost, colour
  [60, 160, "1 · Paper + scoreboard", ["an honest isiXhosa test:", "read, everyday, mixed", "every model, one table"], "~$2 · writing time", CORAL],
  [510, 160, "2 · Mixed-speech Thetha", ["people donate mixed", "sentences (with consent)", "-> train on the real thing"], "consent page · ~$8", NAVY],
  [960, 160, "3 · isiZulu next", ["same recipe, sister", "language: NCHLT and", "FLEURS both have it"], "~$6 a model", NAVY],
  [285, 520, "4 · Subtitles tool", ["isiXhosa video in,", "captions file out", "(for TikTok, YouTube)"], "free · laptop", NAVY],
  [735, 520, "5 · Live on a phone", ["offline, real-time", "captions: the wearable's", "first step"], "hard: speed work", NAVY],
];
for (const [x, y, title, lines, cost, col] of cards) {
  sk.rect(x, y, 380, 300, { w: col === CORAL ? 4.5 : 2.5, color: col });
  sk.text(x + 190, y + 50, title, { size: 28, weight: "bold", color: col });
  sk.text(x + 190, y + 112, lines, { size: 23, lh: 1.45 });
  sk.text(x + 190, y + 262, cost, { size: 22, color: MUTED });
}
sk.text(250, 505, "↑ my pick: start here", { size: 25, weight: "bold", color: CORAL });

// what is out of reach
sk.rect(70, 865, 1260, 85, { w: 2, color: MUTED });
sk.text(700, 900, "not realistic: our own isiXhosa voice (Swivuriso forbids TTS) · out-building Meta on 1,600 languages", { size: 21, color: MUTED });
sk.text(700, 932, "one person + small credits wins by going deep on one language family, not wide", { size: 21, color: EMERALD, weight: "bold" });

render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/ideas.png");
