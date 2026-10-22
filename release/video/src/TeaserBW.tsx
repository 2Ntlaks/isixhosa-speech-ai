// R-0027 teaser, black-and-white cut: plain typing with a human rhythm (and a typo), keyboard sounds, the founder's own
// recording transcribed by the old and the new browser demo. No glow, no grain, no scramble. Every word is real
// (prepare_teaser.py -> teaser.json); the numbers are R-0027's.
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, random, staticFile, useCurrentFrame } from "remotion";
import { loadFont } from "@remotion/google-fonts/IBMPlexMono";
import t from "./teaser.json";

const font = loadFont("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;
const FPS = 30, INK = "#f4f4f2", GREY = "#8c8c88", DIM = "#4a4a48", BG = "#0b0b0b";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/* ---------- typing engine: ops -> keystroke events with a human rhythm ---------- */
type Op = string | { back: number } | { pause: number };
type Ev = { at: number; ch?: string; back?: boolean };
const plan = (ops: Op[], seed: string, pace = 0.5): { evs: Ev[]; end: number } => {
  const evs: Ev[] = [];
  let f = 0, n = 0;
  for (const op of ops) {
    if (typeof op === "string") {
      for (const ch of op) {
        const r = random(`${seed}-${n++}`);
        f += Math.round((1.6 + r * 2.2) * pace);                       // ~9-15 keys a second
        if (ch === " " && r > 0.6) f += Math.round(3 * pace);           // a breath between some words
        evs.push({ at: f, ch });
        if (".,:?!".includes(ch)) f += Math.round(9 * pace);
        if (ch === "\n") f += Math.round(10 * pace);
      }
    } else if ("back" in op) {
      f += 14;                                                          // notice the typo
      for (let k = 0; k < op.back; k++) { f += 3; evs.push({ at: f, back: true }); }
      f += 6;
    } else f += op.pause;
  }
  return { evs, end: f };
};
const textAt = (evs: Ev[], f: number) => {
  let s = "";
  for (const e of evs) { if (e.at > f) break; s = e.back ? s.slice(0, -1) : s + e.ch; }
  return s;
};
const Keys: React.FC<{ evs: Ev[]; seed: string; v?: number }> = ({ evs, seed, v = 0.55 }) => (
  <>{evs.map((e, k) => {
    const src = e.back ? "key_back.wav" : e.ch === " " || e.ch === "\n" ? "key_space.wav" : `key${Math.floor(random(`${seed}k${k}`) * 4)}.wav`;
    return <Sequence key={k} from={e.at} durationInFrames={4} layout="none">
      <Audio src={staticFile(src)} volume={v * (0.75 + 0.5 * random(`${seed}v${k}`))} /></Sequence>;
  })}</>
);
const Cursor: React.FC<{ typing: boolean; f: number }> = ({ typing, f }) =>
  <span style={{ display: "inline-block", width: "0.55em", height: "1.05em", marginLeft: 4, verticalAlign: "-0.15em", background: INK,
    opacity: typing || Math.floor(f / 16) % 2 === 0 ? 1 : 0 }} />;

/* a screen of typed text */
const Typed: React.FC<{ ops: Op[]; seed: string; size: number; top?: number; pace?: number }> = ({ ops, seed, size, top = 640, pace }) => {
  const f = useCurrentFrame(), { evs } = plan(ops, seed, pace), s = textAt(evs, f);
  const typing = evs.some(e => e.at <= f && e.at > f - 5) || (evs[0] && f < evs[0].at + 2 && f >= 0);
  return (
    <AbsoluteFill>
      <Keys evs={evs} seed={seed} />
      <div style={{ position: "absolute", left: 96, right: 96, top, fontFamily: font, fontSize: size, lineHeight: 1.28, color: INK,
        whiteSpace: "pre-wrap", fontWeight: 400 }}>{s}<Cursor typing={typing} f={f} /></div>
    </AbsoluteFill>
  );
};

/* ---------- scenes ---------- */
const HOOK: Op[] = ["the Thetha model\njust got an upgarde", { back: 4 }, "rade."];
const CHANGED: Op[] = ["what changed?", { pause: 10 }, "\n\n245 more hours\nof real people\nspeaking isiXhosa."];
const NUMBER: Op[] = ["letters wrong\nin every 100:", { pause: 8 }, "\n\nbefore  11.8\nnow     5.1"];
const TRY: Op[] = ["free. runs on\nyour phone.", { pause: 8 }, "\n\nlink below ↓"];

const HOLD = 26;  // frames a finished screen stays up
const len = (ops: Op[], seed: string, hold = HOLD) => plan(ops, seed).end + hold;

/* the listening screen: labels typed, then the voice; both versions write it as it is spoken */
const HEAD: Op[] = ["me, speaking isiXhosa ↓"];
const V0 = plan(HEAD, "head").end + 14;                   // voice starts after the header is typed
const VEND = V0 + Math.round(t.seconds * FPS);
const OLD_TALLY: Op[] = [`${t.outputs.old.errors} words wrong`];
const NEW_TALLY: Op[] = [`${t.outputs.new.errors} words wrong (heard "Thetha"\nas "theatre" 😅)`];
const T_OLD = VEND + 22, T_NEW = T_OLD + plan(OLD_TALLY, "to", 0.5).end + 10;
const LISTEN_LEN = T_NEW + plan(NEW_TALLY, "tn", 0.5).end + 50;

type W = { w: string; ok: boolean; t: number };
const Transcript: React.FC<{ label: string; words: W[]; tally: Op[]; tallyAt: number; seed: string; f: number }> =
  ({ label, words, tally, tallyAt, seed, f }) => {
    const tl = plan(tally, seed, 0.5);
    return (
      <div style={{ marginTop: 60 }}>
        <div style={{ fontSize: 34, color: GREY, opacity: f >= 6 ? 1 : 0 }}>{label}</div>
        <div style={{ fontSize: 54, lineHeight: 1.3, color: INK, marginTop: 14, minHeight: 5 * 70 }}>
          {words.map((w, k) => {
            const end = V0 + Math.round(w.t * FPS), start = end - w.w.length, shown = Math.max(0, Math.min(w.w.length, f - start));
            if (shown <= 0) return null;
            const strike = !w.ok ? interpolate(f, [VEND + 6 + k, VEND + 14 + k], [0, 1], clamp) : 0;
            return <span key={k} style={{ position: "relative", display: "inline-block", marginRight: "0.6em", color: strike > 0 ? GREY : INK }}>
              {w.w.slice(0, shown)}
              {strike > 0 && <span style={{ position: "absolute", left: -4, top: "55%", height: 4, width: `calc(${strike * 100}% + 8px)`, background: INK }} />}
            </span>;
          })}
        </div>
        <Sequence from={tallyAt} layout="none"><Keys evs={tl.evs} seed={seed} /></Sequence>
        <div style={{ fontSize: 40, lineHeight: 1.3, color: INK, marginTop: 18, whiteSpace: "pre-wrap", minHeight: 2 * 52 }}>
          {f >= tallyAt ? textAt(tl.evs, f - tallyAt) : ""}</div>
      </div>
    );
  };

const Listen: React.FC = () => {
  const f = useCurrentFrame(), head = plan(HEAD, "head");
  return (
    <AbsoluteFill>
      <Keys evs={head.evs} seed="head" />
      <Sequence from={V0} layout="none"><Audio src={staticFile("teaser_voice.wav")} /></Sequence>
      <div style={{ position: "absolute", left: 96, right: 96, top: 300, fontFamily: font }}>
        <div style={{ fontSize: 46, color: INK }}>{textAt(head.evs, f)}{f < V0 + 10 ? <Cursor typing={f < head.end + 3} f={f} /> : null}</div>
        <Transcript label="old version" words={t.outputs.old.words} tally={OLD_TALLY} tallyAt={T_OLD} seed="to" f={f} />
        <Transcript label="new version" words={t.outputs.new.words} tally={NEW_TALLY} tallyAt={T_NEW} seed="tn" f={f} />
      </div>
    </AbsoluteFill>
  );
};

const SCENES: [number, React.FC][] = [
  [len(HOOK, "hook", 30), () => <Typed ops={HOOK} seed="hook" size={86} top={720} />],
  [LISTEN_LEN, Listen],
  [len(CHANGED, "chg"), () => <Typed ops={CHANGED} seed="chg" size={76} top={660} />],
  [len(NUMBER, "num"), () => <Typed ops={NUMBER} seed="num" size={76} top={660} />],
  [len(TRY, "try", 60), () => <Typed ops={TRY} seed="try" size={76} top={700} />],
];
export const BW_TOTAL = SCENES.reduce((s, [n]) => s + n, 0);

export const TeaserBW: React.FC = () => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: BG }}>
      {SCENES.map(([n, S], i) => { const from = at; at += n;
        return <Sequence key={i} from={from} durationInFrames={n}><S /></Sequence>; })}
    </AbsoluteFill>
  );
};
