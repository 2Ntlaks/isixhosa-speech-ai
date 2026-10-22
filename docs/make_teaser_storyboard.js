// One-sheet storyboard for the R-0027 teaser video (Remotion, vertical). Every transcript shown is a real model output.
const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude-account2/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;

const sk = new Sketch(1400, 1180, 31);
sk.text(700, 60, "Thetha teaser: storyboard (~24 s, vertical)", { size: 40, weight: "bold" });
sk.text(700, 102, "your voice, the real old and new demo outputs, one number, one link", { size: 24, color: MUTED });

const W = 200, H = 340;
const panels = [
  { t: "0-2 s · hook", cx: 233, y: 150, draw: (x, y) => {
      sk.text(x + W / 2, y + 140, ["Thetha got", "an upgrade"], { size: 24, weight: "bold" });
      sk.text(x + W / 2, y + 230, "your voice starts", { size: 17, color: MUTED });
    }, cap: ["black screen, big words,", "your recording begins"] },
  { t: "2-7 s · before", cx: 700, y: 150, draw: (x, y) => {
      sk.text(x + W / 2, y + 40, "old demo", { size: 18, color: MUTED });
      sk.text(x + W / 2, y + 95, ["molweni apho", "kuthwita ..."], { size: 17 });
      sk.text(x + W / 2, y + 165, ["leemodelethe", "tha"], { size: 19, color: CORAL, weight: "bold" });
      sk.text(x + W / 2, y + 235, "ibeluncedo", { size: 19, color: CORAL, weight: "bold" });
      sk.text(x + W / 2, y + 300, "6 of 16 words wrong", { size: 16, color: CORAL });
    }, cap: ["the words type out as you speak;", "mistakes flash coral"] },
  { t: "7-10 s · what changed", cx: 1167, y: 150, draw: (x, y) => {
      for (let i = 0; i < 9; i++) { const h = 18 + ((i * 37) % 50); sk.line(x + 30 + i * 17, y + 120 - h / 2, x + 30 + i * 17, y + 120 + h / 2, { color: NAVY, w: 3 }); }
      sk.line(x + 82, y + 75, x + 82, y + 165, { color: CORAL, w: 2.5 });
      sk.line(x + 133, y + 75, x + 133, y + 165, { color: CORAL, w: 2.5 });
      sk.text(x + W / 2, y + 225, ["+245 hours of", "real isiXhosa"], { size: 20, weight: "bold" });
      sk.text(x + W / 2, y + 295, "long talks, cut at pauses", { size: 15, color: MUTED });
    }, cap: ["a long recording splits", "into pieces at the pauses"] },
  { t: "10-16 s · after", cx: 233, y: 630, draw: (x, y) => {
      sk.text(x + W / 2, y + 40, "new demo", { size: 18, color: EMERALD });
      sk.text(x + W / 2, y + 100, ["molweni apho", "kuthwita ndicela", "... le model"], { size: 17, lh: 1.4 });
      sk.text(x + W / 2, y + 200, "theatre 😅", { size: 20, color: CORAL, weight: "bold" });
      sk.text(x + W / 2, y + 250, ["ukuze ibe luncedo", "... south africa"], { size: 17, lh: 1.4 });
      sk.text(x + W / 2, y + 318, "2 of 16 wrong", { size: 16, color: EMERALD, weight: "bold" });
    }, cap: ["same voice: scrambled letters", "settle into words; honest about 'theatre'"] },
  { t: "16-20 s · the number", cx: 700, y: 630, draw: (x, y) => {
      sk.text(x + W / 2, y + 50, ["letters wrong", "in every 100"], { size: 17, color: MUTED });
      sk.rect(x + 25, y + 120, 150, 34, { color: MUTED, w: 2 });
      sk.text(x + W / 2, y + 185, "11.8 before", { size: 18, color: MUTED });
      sk.rect(x + 25, y + 215, 65, 34, { color: EMERALD, w: 3 });
      sk.text(x + W / 2, y + 285, "5.1 now", { size: 26, color: EMERALD, weight: "bold" });
    }, cap: ["the bar shrinks, the number", "counts down (everyday speech)"] },
  { t: "20-24 s · try it", cx: 1167, y: 630, draw: (x, y) => {
      sk.ellipse(x + W / 2, y + 110, 48, 48, { color: CORAL, w: 3.5 });
      sk.text(x + W / 2, y + 200, ["runs in your browser", "nothing is uploaded"], { size: 16, lh: 1.4 });
      sk.text(x + W / 2, y + 268, "thetha link", { size: 19, weight: "bold", color: CORAL });
      sk.text(x + W / 2, y + 310, "data: DSFSI, UP", { size: 14, color: MUTED });
    }, cap: ["the demo's glowing circle,", "the link, the data credit"] },
];
for (const p of panels) {
  const x = p.cx - W / 2;
  sk.text(p.cx, p.y - 2, p.t, { size: 24, weight: "bold", color: NAVY });
  sk.rect(x, p.y + 18, W, H, { w: 3 });
  sk.line(p.cx - 25, p.y + 32, p.cx + 25, p.y + 32, { color: MUTED, w: 2 });
  p.draw(x, p.y + 18);
  sk.text(p.cx, p.y + H + 58, p.cap, { size: 19, color: MUTED });
}
for (const [x1, x2, y] of [[343, 590, 330], [810, 1057, 330], [343, 590, 810], [810, 1057, 810]]) sk.arrow(x1, y, x2, y, { w: 2.5 });
sk.curveArrow(1167, 590, 700, 600, 233, 600, { w: 2.5, color: MUTED });

sk.line(60, 1090, 1340, 1090, { color: MUTED, w: 1.5 });
sk.text(700, 1130, "all transcripts are real outputs from the old and new browser demo on your recording (20261021-140009) · music synthesised, no licences", { size: 19, color: MUTED });
render(sk, "C:/Users/ntlak/Downloads/isiXhosa Speech AI/docs/teaser-storyboard.png");
