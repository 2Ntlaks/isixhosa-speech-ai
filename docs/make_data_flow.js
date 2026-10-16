const { Sketch, render, COLORS } = require("C:/Users/ntlak/.claude/skills/hand-drawn-diagrams/sketch-lib.js");
const { NAVY, CORAL, MUTED, EMERALD } = COLORS;
const sk = new Sketch(1400, 860, 5);
sk.text(700, 62, "Where the speech data lives", { size: 42, weight: "bold" });
sk.text(700, 104, "downloaded and stored in the cloud; your laptop keeps almost nothing", { size: 24, color: MUTED });

const box = (x, y, w, h, title, lines, color = NAVY) => {
  sk.rect(x, y, w, h, { color, w: 3 });
  sk.text(x + w / 2, y + 52, title, { size: 30, weight: "bold", color });
  sk.text(x + w / 2, y + 96, lines, { size: 24 });
};

// row 1: licence -> downloader -> bucket
box(50, 170, 290, 180, "1 · You", ["log in to SADiLaR,", "accept the licence"]);
box(430, 170, 320, 180, "2 · Downloader", ["small cloud machine,", "~30 min, then off"]);
box(840, 170, 510, 180, "3 · S3 bucket (private)", ["NCHLT + FLEURS, ~6-10 GB", "about $0.20 a month"], CORAL);
sk.arrow(345, 260, 425, 260);
sk.text(385, 225, "link", { size: 22, color: MUTED });
sk.arrow(755, 260, 835, 260);

// FLEURS needs no licence click
box(50, 480, 330, 150, "Hugging Face", ["FLEURS xh_za, public"], MUTED);
sk.arrow(300, 475, 500, 355, { color: MUTED });

// row 2: who reads from the bucket
box(560, 480, 360, 180, "GPU node (stage 2+)", ["reads the full set,", "same region: free"]);
box(1010, 480, 340, 180, "Your laptop (stage 1)", ["only 100 test clips", "+ Whisper, ~1 GB"], EMERALD);
sk.arrow(960, 355, 800, 475);
sk.arrow(1180, 355, 1180, 475);

sk.text(700, 740, "Your disk: about 1 GB instead of about 10 GB.", { size: 28, color: NAVY });
sk.text(700, 790, "Licence: the bucket stays private; raw audio is never shared.", { size: 24, color: MUTED });

render(sk, require("path").join(__dirname, "data-flow.png"));
