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




# The post's drawings are tall (900 wide) so the handwriting stays readable on a phone: a 358 px phone column
# shows them at 0.4x, so 32 px text lands near 13 px. Side-by-side ideas are stacked instead.
W = 900


def voice_to_text(out):
    s = Scene(W, 1300, 12)
    s.text(W / 2, 24, "How a computer turns\nyour voice into text", 42, align="center")
    cells = [(40, 170, "1. sound", "air pressure, wobbling"), (470, 170, "2. numbers", "16 000 every second"),
             (40, 610, "3. sound picture", "which pitches, over time"), (470, 610, "4. the model writes", "one piece at a time")]
    for x, y, t, n in cells:
        s.box(x, y, 390, 360)
        s.text(x + 195, y + 18, t, 34, align="center")
        s.text(x + 195, y + 372, n, 28, MUTED, align="center")
    s.arrow([(436, 350), (466, 350)], CORAL, sw=3)
    s.arrow([(436, 790), (466, 790)], CORAL, sw=3)
    pts = [(70 + k * 5.6, 375 + math.sin(k * 0.55) * (14 + 60 * abs(math.sin(k * 0.09)))) for k in range(60)]
    s.line(pts, NAVY, sw=3)
    s.text(665, 230, "0.02\n-0.11\n0.37\n-0.29\n…", 36, NAVY, align="center")
    rr = random.Random(5)
    for cx in range(12):
        for cy in range(10):
            v = abs(math.sin(cx * 0.7) * math.cos(cy * 0.5)) * rr.random()
            col = NAVY if v > 0.5 else "#5b7aa6" if v > 0.25 else BLUE_BG
            s.box(75 + cx * 27, 680 + cy * 26, 24, 23, stroke="transparent", bg=col, rounded=False, roughness=0, sw=1)
    for j, w in enumerate(["esi", "sibini", "sino…"]):
        s.box(510, 690 + j * 86, 310, 68, bg=GREEN_BG if j < 2 else WHITE, stroke=GREEN if j < 2 else NAVY, dashed=j == 2)
        s.text(665, 703 + j * 86, w, 34, align="center")
    s.box(40, 1060, 820, 200, bg=WHITE, stroke=MUTED, dashed=True)
    s.text(W / 2, 1078, "Step 4 is a guess, based on what it heard\nand what it already wrote.", 30, align="center")
    s.text(W / 2, 1170, "Never heard isiXhosa? It guesses Swahili,\nor gets stuck: kwa kwa kwa kwa", 30, RED, align="center")
    s.save(os.path.join(out, "voice-to-text.excalidraw"))


def training_loop(out):
    s = Scene(W, 1080, 13)
    s.text(W / 2, 24, "Teaching it a new language:\none training step", 42, align="center")
    boxes = [(40, 170, "1. listen", "a clip and its\ntrue text", False), (480, 170, "2. guess", "it writes what it\nthinks it heard", False),
             (480, 560, "3. compare", "count what's different\n(the \"loss\")", False), (40, 560, "4. nudge", "change 769 million\nnumbers a tiny bit", True)]
    for x, y, t, sub, g in boxes:
        s.box(x, y, 380, 230, bg=GREEN_BG if g else WHITE, stroke=GREEN if g else NAVY)
        s.text(x + 190, y + 26, t, 38, GREEN if g else NAVY, align="center")
        s.text(x + 190, y + 96, sub, 30, MUTED, align="center")
    s.arrow([(425, 285), (475, 285)], CORAL, sw=3)
    s.arrow([(670, 405), (670, 550)], CORAL, sw=3)
    s.arrow([(475, 675), (425, 675)], CORAL, sw=3)
    s.arrow([(230, 550), (230, 405)], CORAL, sw=3)
    s.text(W / 2, 445, "repeat 4 000 times,\n32 clips at a time", 32, align="center")
    s.text(W / 2, 840, "before training: kwa kwa kwa kwa", 30, RED, align="center")
    s.text(W / 2, 890, "after training: esi sibini sinokukhetha…", 30, GREEN, align="center")
    s.text(W / 2, 950, "(whisper-medium, the model behind the 8% score)", 24, MUTED, align="center")
    s.save(os.path.join(out, "training-loop.excalidraw"))


def leaked_exam(out):
    s = Scene(W, 1480, 14)
    s.text(W / 2, 24, "The trap: a test that\nhas seen the answers", 42, align="center")
    # top: the leaky test
    s.box(40, 170, 820, 600, bg=WHITE, stroke=RED)
    s.text(W / 2, 192, "the test I first trusted", 36, RED, align="center")
    s.ellipse(80, 260, 600, 330, bg=BLUE_BG)
    s.text(380, 290, "study notes\n(training sentences)", 28, MUTED, align="center")
    rr = random.Random(3)
    for k in range(11):
        inside = k < 9
        x = 160 + (k % 5) * 92 + rr.randint(-6, 6) if inside else 720 + (k - 9) * 40
        y = 380 + (k // 5) * 96 + rr.randint(-5, 5) if inside else 300 + (k - 9) * 110
        s.box(x, y, 64, 76, bg=WHITE, stroke=NAVY, sw=2)
        s.line([(x + 12, y + 24), (x + 52, y + 24)], MUTED, sw=1.5)
        s.line([(x + 12, y + 44), (x + 44, y + 44)], MUTED, sw=1.5)
    s.text(W / 2, 612, "82% of the test sentences were\nones it had already studied", 30, NAVY, align="center")
    s.text(W / 2, 700, "3% of letters wrong", 44, RED, align="center")
    # bottom: the honest test
    s.box(40, 810, 820, 560, bg=WHITE, stroke=GREEN)
    s.text(W / 2, 832, "the honest test", 36, GREEN, align="center")
    for k in range(6):
        x, y = 160 + (k % 3) * 210, 900 + (k // 3) * 140
        s.box(x, y, 120, 116, bg=WHITE)
        for j in range(3):
            s.line([(x + 18, y + 30 + j * 26), (x + 100 - j * 14, y + 30 + j * 26)], MUTED, sw=1.5)
    s.text(W / 2, 1180, "brand new, longer sentences in a\ndifferent style (Google FLEURS)", 30, NAVY, align="center")
    s.text(W / 2, 1280, "30% of letters wrong", 44, GREEN, align="center")
    s.text(W / 2, 1400, "A score only means something if the\nanswers weren't in the study notes.", 30, NAVY, align="center")
    s.save(os.path.join(out, "leaked-exam.excalidraw"))


def where_it_runs(out):
    s = Scene(W, 1440, 16)
    s.text(W / 2, 24, "Where the model runs", 42, align="center")

    def phone(x, y):
        s.box(x, y, 160, 290, bg=WHITE, sw=3)
        s.box(x + 16, y + 26, 128, 214, bg=BLUE_BG, sw=1.5)
        s.ellipse(x + 67, y + 252, 26, 26, bg=WHITE, sw=1.5)
    # top: a server
    s.box(40, 110, 820, 600, bg=WHITE, stroke=RED)
    s.text(W / 2, 132, "on a server", 36, RED, align="center")
    phone(110, 220)
    s.box(590, 230, 200, 270, bg=BLUE_BG)
    for k in range(4):
        s.line([(615, 275 + k * 56), (765, 275 + k * 56)], NAVY, sw=2)
    s.text(690, 510, "server", 28, MUTED, align="center")
    s.arrow([(290, 310), (575, 310)], CORAL, sw=3)
    s.text(432, 262, "your voice", 28, NAVY, align="center")
    s.arrow([(575, 420), (290, 420)], NAVY, sw=3)
    s.text(432, 432, "the text", 28, NAVY, align="center")
    s.text(W / 2, 580, "$9 a month to keep it switched on,\nand your voice leaves your phone", 32, RED, align="center")
    # bottom: in the browser
    s.box(40, 750, 820, 600, bg=WHITE, stroke=GREEN)
    s.text(W / 2, 772, "in your browser (what Thetha does)", 34, GREEN, align="center")
    phone(370, 850)
    s.ellipse(408, 910, 84, 84, bg=CORAL, stroke=NAVY)
    s.ellipse(436, 938, 28, 28, bg=NAVY)
    s.text(450, 1000, "model", 24, NAVY, align="center")
    s.arrow([(720, 930), (545, 960)], NAVY, dashed=True, sw=3)
    s.text(720, 860, "downloads\n~300 MB, once", 28, MUTED, align="center")
    s.text(W / 2, 1200, "free, and your voice never\nleaves your phone", 32, GREEN, align="center")
    s.tick(720, 1205)
    s.text(W / 2, 1380, "The trade: a one-time download and a few\nseconds of waiting per recording.", 28, MUTED, align="center")
    s.save(os.path.join(out, "where-it-runs.excalidraw"))


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for fn in (voice_to_text, training_loop, leaked_exam, where_it_runs):
        fn(out)
    print("written to", out)
