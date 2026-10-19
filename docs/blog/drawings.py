"""Excalidraw drawings for the ntlaks.dev post about this project, in the blog's house style (Excalifont, navy ink,
coral accent, green for good, off-white paper). Writes .excalidraw sources; docs/blog/render.mjs exports the PNGs.

  python docs/blog/drawings.py <out dir>
Every number drawn here comes from a run in results.md.
"""
import json
import math
import os
import random
import sys

NAVY, MUTED, GREEN, GREEN_BG, RED, CORAL, BLUE_BG, WHITE = "#142a47", "#5f6977", "#047857", "#d5efe3", "#c24530", "#f4715f", "#dfe7f2", "#ffffff"
PAPER = "#f8f7f4"
HAND, CW = 5, 0.52  # Excalifont; average glyph width / font size


class Scene:
    def __init__(self, w, h, seed):
        self.els, self.rnd, self.n = [], random.Random(seed), 0
        self._base("rectangle", 0, 0, w, h, stroke="transparent", roughness=0)  # fixes the export size

    def _base(self, kind, x, y, w, h, stroke=NAVY, bg="transparent", **kw):
        self.n += 1
        e = {"id": f"e{self.n:04d}{self.rnd.randrange(16 ** 6):06x}", "type": kind, "x": x, "y": y, "width": w, "height": h,
             "angle": 0, "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid", "strokeWidth": 2,
             "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
             "seed": self.rnd.randrange(2 ** 31), "version": 1, "versionNonce": self.rnd.randrange(2 ** 31), "isDeleted": False,
             "boundElements": None, "updated": 1, "link": None, "locked": False}
        e.update(kw)
        self.els.append(e)
        return e

    def text(self, x, y, s, size=26, color=NAVY, align="left", w=None):
        lines = s.split("\n")
        width = w if w is not None else max(len(l) for l in lines) * size * CW
        if align == "center" and w is None:
            x -= width / 2
        return self._base("text", x, y, width, len(lines) * size * 1.25, stroke=color, text=s, originalText=s, fontSize=size,
                          fontFamily=HAND, textAlign=align, verticalAlign="top", containerId=None, autoResize=False, lineHeight=1.25)

    def box(self, x, y, w, h, stroke=NAVY, bg=WHITE, sw=2.5, dashed=False, rounded=True, roughness=1):
        return self._base("rectangle", x, y, w, h, stroke=stroke, bg=bg, strokeWidth=sw, roughness=roughness,
                          strokeStyle="dashed" if dashed else "solid", roundness={"type": 3} if rounded else None)

    def ellipse(self, x, y, w, h, stroke=NAVY, bg=WHITE, sw=2.5):
        return self._base("ellipse", x, y, w, h, stroke=stroke, bg=bg, strokeWidth=sw)

    def arrow(self, pts, color=NAVY, sw=2.5, head="arrow", dashed=False, curved=False):
        x0, y0 = pts[0]
        rel = [[px - x0, py - y0] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        return self._base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), stroke=color, strokeWidth=sw, points=rel,
                          lastCommittedPoint=None, startBinding=None, endBinding=None, startArrowhead=None, endArrowhead=head,
                          strokeStyle="dashed" if dashed else "solid", roundness={"type": 2} if curved else None, elbowed=False)

    def line(self, pts, color=NAVY, sw=2.5, dashed=False, curved=False):
        x0, y0 = pts[0]
        rel = [[px - x0, py - y0] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        return self._base("line", x0, y0, max(xs) - min(xs), max(ys) - min(ys), stroke=color, strokeWidth=sw, points=rel,
                          lastCommittedPoint=None, startBinding=None, endBinding=None, startArrowhead=None, endArrowhead=None,
                          strokeStyle="dashed" if dashed else "solid", roundness={"type": 2} if curved else None)

    def person(self, cx, top, s=1.0, color=NAVY):
        self.ellipse(cx - 28 * s, top, 56 * s, 56 * s, stroke=color, bg=WHITE)
        self.line([(cx, top + 56 * s), (cx, top + 150 * s)], color)
        self.line([(cx - 45 * s, top + 95 * s), (cx, top + 78 * s), (cx + 45 * s, top + 95 * s)], color)
        self.line([(cx - 35 * s, top + 215 * s), (cx, top + 150 * s), (cx + 35 * s, top + 215 * s)], color)

    def tick(self, x, y, s=1.0):
        self.line([(x, y + 14 * s), (x + 12 * s, y + 28 * s), (x + 36 * s, y)], GREEN, sw=4)

    def cross(self, x, y, s=1.0):
        self.line([(x, y), (x + 30 * s, y + 30 * s)], RED, sw=4)
        self.line([(x + 30 * s, y), (x, y + 30 * s)], RED, sw=4)

    def save(self, path):
        doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": self.els,
               "appState": {"viewBackgroundColor": PAPER, "gridSize": None}, "files": {}}
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)


def cover(out):
    s = Scene(1400, 720, 11)
    s.person(170, 250, 1.1)
    s.box(40, 40, 470, 150, bg=WHITE)
    s.line([(170, 190), (190, 240)], NAVY)
    s.text(275, 62, "esi sibini sinokukhetha\nukwenza isicwangciso…", 30, align="center")
    s.text(275, 148, "a real isiXhosa sentence", 22, MUTED, align="center")
    s.box(470, 300, 250, 190, bg=BLUE_BG)
    s.ellipse(540, 345, 34, 34, bg=NAVY)
    s.ellipse(616, 345, 34, 34, bg=NAVY)
    s.line([(555, 425), (595, 440), (635, 425)], NAVY, curved=True)
    s.text(595, 500, "Whisper", 34, align="center")
    s.arrow([(260, 400), (455, 395)], NAVY)
    # before
    s.box(830, 60, 520, 230, stroke=RED, bg="#fbe9e5")
    s.text(855, 80, "before", 26, RED)
    s.text(855, 120, "Sisi bini suyo kiki kwa kwa kwa\nkwa kwa kwa kwa kwa kwa kwa\nkwa kwa kwa kwa kwa kwa…", 28, NAVY)
    s.cross(1290, 80)
    s.arrow([(735, 360), (815, 230)], CORAL)
    # after
    s.box(830, 410, 520, 230, stroke=GREEN, bg=GREEN_BG)
    s.text(855, 430, "after I taught it", 26, GREEN)
    s.text(855, 470, "esi sibini sinokukhetha ukwenza\nisicwangciso sokwamkelwa\nkomntwana waso", 28, NAVY)
    s.tick(1285, 430)
    s.arrow([(735, 430), (815, 520)], CORAL)
    s.save(os.path.join(out, "cover.excalidraw"))


def voice_to_text(out):
    s = Scene(1400, 820, 12)
    s.text(700, 30, "How a computer turns your voice into text", 40, align="center")
    xs = [40, 380, 720, 1060]
    titles = ["1. sound", "2. numbers", "3. sound picture", "4. the model writes"]
    notes = ["air pressure, wobbling", "16 000 of them every second", "which pitches, over time", "one piece at a time"]
    for i, x in enumerate(xs):
        s.box(x, 110, 300, 330)
        s.text(x + 150, 125, titles[i], 28, align="center")
        s.text(x + 150, 455, notes[i], 22, MUTED, align="center")
        if i < 3:
            s.arrow([(x + 305, 275), (x + 335, 275)], CORAL)
    pts = [(70 + k * 4.2, 290 + math.sin(k * 0.55) * (12 + 48 * abs(math.sin(k * 0.09)))) for k in range(58)]
    s.line(pts, NAVY, sw=2.5)
    s.text(530, 190, "0.02\n-0.11\n0.37\n-0.29\n0.08\n…", 28, NAVY, align="center")
    rr = random.Random(5)
    for cx in range(14):
        for cy in range(9):
            v = abs(math.sin(cx * 0.7) * math.cos(cy * 0.5)) * rr.random()
            col = NAVY if v > 0.5 else "#5b7aa6" if v > 0.25 else BLUE_BG
            s.box(745 + cx * 18, 195 + cy * 22, 16, 20, stroke="transparent", bg=col, rounded=False, roughness=0, sw=1)
    for j, w in enumerate(["esi", "sibini", "sino…"]):
        s.box(1090, 185 + j * 72, 240, 56, bg=GREEN_BG if j < 2 else WHITE, stroke=GREEN if j < 2 else NAVY, dashed=j == 2)
        s.text(1210, 196 + j * 72, w, 28, align="center")
    s.box(140, 560, 1120, 190, bg=WHITE, stroke=MUTED, dashed=True)
    s.text(700, 580, "Step 4 is a guess, based on what it heard and what it already wrote.", 28, align="center")
    s.text(700, 640, "If it has never heard isiXhosa, its best guess is a language it does know (Swahili),", 26, MUTED, align="center")
    s.text(700, 690, "or it gets stuck repeating itself: kwa kwa kwa kwa", 26, RED, align="center")
    s.save(os.path.join(out, "voice-to-text.excalidraw"))


def training_loop(out):
    s = Scene(1400, 860, 13)
    s.text(700, 30, "Teaching it a new language: one training step", 40, align="center")
    pos = [(470, 120), (870, 340), (470, 560), (70, 340)]
    t = ["1. listen", "2. guess", "3. compare", "4. nudge"]
    sub = ["a clip and its true text", "the model writes what\nit thinks it heard", "count what's different\n(this is the \"loss\")",
           "change 769 million numbers\na tiny bit to do better"]
    for i, (x, y) in enumerate(pos):
        s.box(x, y, 460, 170, bg=GREEN_BG if i == 3 else WHITE, stroke=GREEN if i == 3 else NAVY)
        s.text(x + 230, y + 22, t[i], 32, GREEN if i == 3 else NAVY, align="center")
        s.text(x + 230, y + 72, sub[i], 24, MUTED, align="center")
    s.arrow([(935, 210), (1080, 210), (1100, 330)], CORAL, curved=True)
    s.arrow([(1100, 515), (1080, 640), (935, 650)], CORAL, curved=True)
    s.arrow([(465, 650), (320, 640), (300, 515)], CORAL, curved=True)
    s.arrow([(300, 335), (320, 210), (465, 210)], CORAL, curved=True)
    s.text(700, 395, "repeat 4 000 times", 30, align="center")
    s.text(700, 445, "32 clips at a time", 26, MUTED, align="center")
    s.text(700, 760, "before training: kwa kwa kwa kwa · after training: esi sibini sinokukhetha…", 24, MUTED, align="center")
    s.text(700, 802, "(whisper-medium, the model behind the 8% score)", 20, MUTED, align="center")
    s.save(os.path.join(out, "training-loop.excalidraw"))


def leaked_exam(out):
    s = Scene(1400, 820, 14)
    s.text(700, 30, "The trap: a test that has seen the answers", 40, align="center")
    # left: the leaky test
    s.box(40, 110, 620, 560, bg=WHITE, stroke=RED)
    s.text(350, 130, "the test I first trusted", 30, RED, align="center")
    s.ellipse(90, 200, 520, 300, bg=BLUE_BG)
    s.text(350, 262, "study notes (training sentences)", 24, MUTED, align="center")
    rr = random.Random(3)
    for k in range(11):
        inside = k < 9
        x = 150 + (k % 6) * 72 + rr.randint(-8, 8) if inside else 535 + (k - 9) * 50
        y = 300 + (k // 6) * 80 + rr.randint(-6, 6) if inside else 172 + (k - 9) * 14
        s.box(x, y, 52, 60, bg=WHITE, stroke=NAVY, sw=2)
        s.line([(x + 10, y + 18), (x + 42, y + 18)], MUTED, sw=1.5)
        s.line([(x + 10, y + 34), (x + 36, y + 34)], MUTED, sw=1.5)
    s.text(350, 520, "82% of the test clips were sentences\nit had already studied", 24, NAVY, align="center")
    s.text(350, 600, "3% of letters wrong", 36, RED, align="center")
    # right: the honest test
    s.box(740, 110, 620, 560, bg=WHITE, stroke=GREEN)
    s.text(1050, 130, "the honest test", 30, GREEN, align="center")
    for k in range(6):
        x, y = 830 + (k % 3) * 150, 230 + (k // 3) * 120
        s.box(x, y, 90, 100, bg=WHITE)
        for j in range(3):
            s.line([(x + 14, y + 25 + j * 22), (x + 76 - j * 10, y + 25 + j * 22)], MUTED, sw=1.5)
    s.text(1050, 480, "brand new, longer sentences\nin a different style (Google FLEURS)", 24, NAVY, align="center")
    s.text(1050, 600, "30% of letters wrong", 36, GREEN, align="center")
    s.text(700, 720, "A score only means something if the answers weren't in the study notes.", 28, NAVY, align="center")
    s.save(os.path.join(out, "leaked-exam.excalidraw"))


def progress(out):
    s = Scene(1400, 820, 15)
    s.text(700, 30, "Letters wrong on sentences it never heard", 40, align="center")
    s.text(700, 88, "Google FLEURS isiXhosa test, 1 034 clips · lower is better", 24, MUTED, align="center")
    bars = [("stock\nwhisper-small", 65.45), ("stock\nwhisper-medium", 45.86), ("small, taught\non NCHLT", 29.81),
            ("small, + FLEURS\nsentences", 10.16), ("medium, + FLEURS\nsentences", 8.03)]
    base, top, left = 640, 170, 130
    y = lambda v: base - v / 70 * (base - top)
    for t in (0, 20, 40, 60):
        s.line([(left - 20, y(t)), (1340, y(t))], "#c9ced6", sw=1, dashed=t > 0)
        s.text(left - 30, y(t) - 14, f"{t}%", 22, MUTED, align="right", w=60) if False else s.text(left - 95, y(t) - 15, f"{t}%", 22, MUTED)
    for i, (lab, v) in enumerate(bars):
        x, best = left + 30 + i * 240, i == 4
        s.box(x, y(v), 150, base - y(v), stroke=CORAL if best else NAVY, bg="#fde3dc" if best else BLUE_BG, rounded=False)
        s.text(x + 75, y(v) - 44, f"{v:.1f}%", 30, CORAL if best else NAVY, align="center")
        s.text(x + 75, base + 18, lab, 22, NAVY, align="center")
    s.line([(left - 20, base), (1340, base)], NAVY, sw=3)
    s.save(os.path.join(out, "progress.excalidraw"))


def where_it_runs(out):
    s = Scene(1400, 800, 16)
    s.text(700, 30, "Where the model runs", 40, align="center")

    def phone(x, y):
        s.box(x, y, 150, 270, bg=WHITE, sw=3)
        s.box(x + 15, y + 25, 120, 200, bg=BLUE_BG, sw=1.5)
        s.ellipse(x + 63, y + 235, 24, 24, bg=WHITE, sw=1.5)
    # left: a server
    s.box(40, 110, 620, 560, bg=WHITE, stroke=RED)
    s.text(350, 130, "on a server", 30, RED, align="center")
    phone(90, 220)
    s.box(430, 230, 180, 240, bg=BLUE_BG)
    for k in range(4):
        s.line([(455, 270 + k * 50), (585, 270 + k * 50)], NAVY, sw=2)
    s.text(520, 480, "server", 24, MUTED, align="center")
    s.arrow([(250, 300), (420, 300)], CORAL)
    s.text(335, 255, "your voice", 22, NAVY, align="center")
    s.arrow([(420, 400), (250, 400)], NAVY)
    s.text(335, 410, "the text", 22, NAVY, align="center")
    s.text(350, 550, "$9 a month to keep it switched on,\nand your voice leaves your phone", 26, RED, align="center")
    # right: in the browser
    s.box(740, 110, 620, 560, bg=WHITE, stroke=GREEN)
    s.text(1050, 130, "in your browser (what Thetha does)", 28, GREEN, align="center")
    phone(975, 200)
    s.ellipse(1012, 260, 76, 76, bg=CORAL, stroke=NAVY)
    s.ellipse(1037, 285, 26, 26, bg=NAVY)
    s.text(1050, 345, "model", 20, NAVY, align="center")
    s.arrow([(1260, 300), (1140, 330)], NAVY, dashed=True)
    s.text(1265, 230, "downloads\n~300 MB, once", 22, MUTED, align="center")
    s.text(1050, 520, "free, and your voice never\nleaves your phone", 26, GREEN, align="center")
    s.tick(1255, 512)
    s.text(700, 720, "The trade: a one-time download and a few seconds of waiting per recording.", 26, MUTED, align="center")
    s.save(os.path.join(out, "where-it-runs.excalidraw"))


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for fn in (cover, voice_to_text, training_loop, leaked_exam, progress, where_it_runs):
        fn(out)
    print("written to", out)
