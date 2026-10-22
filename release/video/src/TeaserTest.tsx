// R-0027 teaser, "listening test" cut: the AI sits an isiXhosa listening test twice. The question is the founder's own
// recording (from "siphuhlise"); the answers are the old and new browser demo's real outputs; a teacher's red pen marks
// them with the real scores (prepare_teaser.py -> teaser.json). Black-and-white typing in between, red pen the only colour.
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, random, staticFile, useCurrentFrame } from "remotion";
import { loadFont as loadHand } from "@remotion/google-fonts/Caveat";
import { loadFont as loadType } from "@remotion/google-fonts/CourierPrime";
import { Op, Typed, plan } from "./TeaserBW";
import t from "./teaser.json";

const hand = loadHand("normal", { weights: ["600", "700"], subsets: ["latin"] }).fontFamily;
const type = loadType("normal", { weights: ["400", "700"], subsets: ["latin"] }).fontFamily;
const FPS = 30, RED = "#c8231b", INKB = "#1f2a44", PAPER = "#f3efe4", RULE = "#b9c8da";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.3, 0.7, 0.2, 1);
type W = { w: string; ok: boolean; t: number };

/* a pen stroke that draws itself */
const roughEllipse = (seed: string) => {
  const pts: string[] = [], turns = 1.13, a0 = -2.4 + random(seed) * 0.6;
  for (let i = 0; i <= 48; i++) {
    const a = a0 + (i / 48) * Math.PI * 2 * turns, wob = 1 + (random(`${seed}${i}`) - 0.5) * 0.08 + i * 0.0015;
    pts.push(`${50 + Math.cos(a) * 48 * wob},${50 + Math.sin(a) * 44 * wob}`);
  }
  return "M" + pts.join(" L");
};
const Stroke: React.FC<{ d: string; p: number; w?: number; vb?: string; style?: React.CSSProperties }> = ({ d, p, w = 4.5, vb = "0 0 100 100", style }) =>
  <svg viewBox={vb} preserveAspectRatio="none" style={{ position: "absolute", overflow: "visible", pointerEvents: "none", ...style }}>
    <path d={d} pathLength={1} fill="none" stroke={RED} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"
      vectorEffect="non-scaling-stroke" strokeDasharray={1} strokeDashoffset={1 - p} opacity={p > 0 ? 0.92 : 0} />
  </svg>;
/* handwriting that appears left to right, as if written */
const Written: React.FC<{ text: string; p: number; size: number; color?: string; style?: React.CSSProperties }> = ({ text, p, size, color = RED, style }) =>
  <div style={{ fontFamily: hand, fontWeight: 700, fontSize: size, color, lineHeight: 1, whiteSpace: "nowrap",
    clipPath: `inset(-20% ${(1 - p) * 100}% -20% -5%)`, ...style }}>{text}</div>;
const Pen: React.FC<{ at: number; src: string; v?: number }> = ({ at, src, v = 0.9 }) =>
  <Sequence from={at} durationInFrames={40} layout="none"><Audio src={staticFile(src)} volume={v} /></Sequence>;

/* one sitting of the test */
const V0 = 30, VLEN = Math.round((t.test.end - t.test.start) * FPS), VEND = V0 + VLEN, MARK = VEND + 10;
const draw = (f: number, at: number, dur = 11) => interpolate(f, [at, at + dur], [0, 1], { ...clamp, easing: ease });
const Sheet: React.FC<{ v: "old" | "new" }> = ({ v }) => {
  const f = useCurrentFrame(), ver = t.test.versions[v], isNew = v === "new";
  const wrong = ver.words.map((w, k) => (!w.ok ? k : -1)).filter(k => k >= 0);
  const circleAt = (n: number) => MARK + n * 13;
  const SCORE = circleAt(wrong.length) + 8, NOTE = SCORE + 24;
  const slide = interpolate(f, [0, 16], [1, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
  const drift = Math.sin(f / 45) * 0.35, zoom = 1 + f * 0.00009;
  const lv = (k: number) => { const i = Math.round(t.test.start * FPS) + f - V0 + k; return f >= V0 && f < VEND ? (t.level[i] ?? 0) : 0; };
  const voiceStart = Math.round(t.test.start * FPS);
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 80% at 50% 40%, #2a2826 0%, #121110 75%)" }}>
      <Audio src={staticFile("paper_slide.wav")} volume={0.9} />
      <Sequence from={V0} layout="none"><Audio src={staticFile("teaser_voice.wav")} trimBefore={voiceStart} /></Sequence>
      <Pen at={10} src="pen_write.wav" v={0.55} />
      {wrong.map((_, n) => <Pen key={n} at={circleAt(n)} src="pen_circle.wav" />)}
      {isNew && <Pen at={MARK + 2} src="pen_tick.wav" />}
      <Pen at={SCORE} src="pen_write.wav" />
      <Pen at={NOTE} src="pen_write.wav" v={0.7} />
      <AbsoluteFill style={{ transform: `scale(${1.17 * zoom}) rotate(${drift}deg)`, transformOrigin: "50% 12%" }}>
        <div style={{ position: "absolute", left: 70, top: 170, width: 940, height: 1340, background: PAPER, borderRadius: 6,
          boxShadow: "0 40px 90px -20px #000c, 0 4px 14px #0006",
          transform: `translateY(${slide * 1500}px) rotate(${-1.6 + slide * 9}deg)`,
          backgroundImage: `linear-gradient(90deg, transparent 118px, #dc9a9a 118px, #dc9a9a 121px, transparent 121px),
            repeating-linear-gradient(180deg, transparent 0 77px, ${RULE} 77px 79px)`, backgroundPosition: "0 0, 0 330px", backgroundRepeat: "no-repeat, repeat-y" }}>
          {/* printed header */}
          <div style={{ position: "absolute", left: 150, right: 50, top: 46, fontFamily: type, color: "#2b2b2b" }}>
            <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: "0.04em" }}>isiXhosa LISTENING TEST</div>
            <div style={{ fontSize: 30, marginTop: 18, display: "flex", alignItems: "baseline", gap: 14 }}>Name:
              <Written text={`Thetha (${isNew ? "new" : "old"})`} p={draw(f, 12, 18)} size={60} color={INKB} /></div>
            <div style={{ fontSize: 30, marginTop: 14 }}>Q1. Listen, then write down what you hear.</div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, height: 40, marginTop: 12 }}>
              <span style={{ fontSize: 26, color: "#6b6b66", marginRight: 10 }}>{"▶"} audio</span>
              {Array.from({ length: 30 }, (_, k) => <div key={k} style={{ width: 6, borderRadius: 3, background: "#8d8a82",
                height: 6 + lv(k - 15) * 34 * (0.6 + 0.4 * Math.sin(k * 1.7 + f / 3)) }} />)}
            </div>
          </div>
          {/* the answer, written as the voice is heard */}
          <div style={{ position: "absolute", left: 150, right: 60, top: 330 + 79 - 64, fontFamily: type, fontSize: 52, lineHeight: "79px", color: "#1d1d1b" }}>
            {ver.words.map((w: W, k: number) => {
              const end = V0 + Math.round((w.t - t.test.start) * FPS), start = end - w.w.length;
              const shown = Math.max(0, Math.min(w.w.length, f - start));
              if (shown <= 0) return null;
              const n = wrong.indexOf(k);
              return <span key={k} style={{ position: "relative", display: "inline-block", marginRight: "0.55em" }}>{w.w.slice(0, shown)}
                {n >= 0 && <Stroke d={roughEllipse(`${v}${k}`)} p={draw(f, circleAt(n), 12)} style={{ left: -22, right: -22, top: 4, bottom: -2, width: "calc(100% + 44px)", height: "100%" }} />}
              </span>;
            })}
          </div>
          {/* a tick down the margin for the retake */}
          {isNew && <Stroke d="M10,55 L38,85 L92,10" p={draw(f, MARK + 2, 9)} w={7} style={{ left: 22, top: 360, width: 80, height: 80 }} />}
          {/* the score */}
          <div style={{ position: "absolute", left: 470, top: 700, width: 250, height: 175 }}>
            <Written text={`${ver.right}/${ver.of}`} p={draw(f, SCORE, 18)} size={118} style={{ position: "absolute", left: 22, top: 22 }} />
            <Stroke d={roughEllipse(`score${v}`)} p={draw(f, SCORE + 12, 14)} w={5} style={{ left: 0, top: 0, width: "100%", height: "100%" }} />
          </div>
          {!isNew && <Written text="see me after class." p={draw(f, NOTE, 26)} size={68} style={{ position: "absolute", left: 160, top: 930, transform: "rotate(-4deg)" }} />}
          {isNew && <Written text={'"Thetha", not "theatre" 😅'} p={draw(f, NOTE, 26)} size={54} style={{ position: "absolute", left: 160, top: 925, transform: "rotate(-3deg)" }} />}
          {isNew && <Written text="much better!" p={draw(f, NOTE + 30, 20)} size={74} style={{ position: "absolute", left: 330, top: 1020, transform: "rotate(-5deg)" }} />}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
const SHEET_LEN = (v: "old" | "new") => {
  const wrong = t.test.versions[v].words.filter(w => !w.ok).length;
  return MARK + wrong * 13 + 8 + 24 + (v === "new" ? 30 + 20 : 26) + 26;
};

/* ---------- the film ---------- */
const HOOK: Op[] = ["I gave my AI an\nisiXhosa listening tset", { back: 3 }, "est."];
const STUDY: Op[] = ["so it studied.", { pause: 8 }, "\n\n245 more hours of\nreal isiXhosa speech."];
const END: Op[] = ["the Thetha model\njust got an upgrade.", { pause: 8 }, "\n\nfree, on your phone.\nlink below ↓"];
const tl = (ops: Op[], seed: string, hold: number) => plan(ops, seed).end + hold;

const SCENES: [number, React.FC][] = [
  [tl(HOOK, "thook", 26), () => <Typed ops={HOOK} seed="thook" size={80} top={760} />],
  [SHEET_LEN("old"), () => <Sheet v="old" />],
  [tl(STUDY, "tstudy", 20), () => <Typed ops={STUDY} seed="tstudy" size={76} top={700} />],
  [SHEET_LEN("new"), () => <Sheet v="new" />],
  [tl(END, "tend", 50), () => <Typed ops={END} seed="tend" size={76} top={680} />],
];
export const TEST_TOTAL = SCENES.reduce((s, [n]) => s + n, 0);

export const TeaserTest: React.FC = () => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: "#0b0b0b" }}>
      {SCENES.map(([n, S], i) => { const from = at; at += n;
        return <Sequence key={i} from={from} durationInFrames={n}><S /></Sequence>; })}
    </AbsoluteFill>
  );
};
