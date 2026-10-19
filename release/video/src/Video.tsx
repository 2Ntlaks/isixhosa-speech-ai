// "Thetha" launch film, cut 2: kinetic type on a 100 BPM grid (1 beat = 18 frames), score from sound.py.
// Every transcript on screen is a real run output (prepare.py -> data.json). Frame-driven animation only.
import React from "react";
import {
  AbsoluteFill, Audio, Easing, Sequence, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { loadFont as loadSerif } from "@remotion/google-fonts/InstrumentSerif";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadGrot } from "@remotion/google-fonts/BricolageGrotesque";
import data from "./data.json";

export const serif = loadSerif("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
loadSerif("italic", { weights: ["400"], subsets: ["latin"] });
export const mono = loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily;
export const grot = loadGrot("normal", { weights: ["800"], subsets: ["latin"] }).fontFamily;

export const C = { bg: "#0c0a08", ink: "#f2e9d8", soft: "#a39883", faint: "#5e564a", line: "#2a241c",
  ember: "#e2732b", glow: "#ffb067", ok: "#6fd0a6", err: "#ff6b57" };
export const FPS = 30, BT = 18;  // frames per beat at 100 BPM
export const b = (beats: number) => Math.round(beats * BT);
type Clip = (typeof data.clips)["loop"];
export const clips = data.clips as Record<"loop" | "train" | "east", Clip>;

// sections, in beats (must match sound.py)
const SEC = { open: [0, 4], reel: [4, 10], flood: [10, 17], taught: [17, 20], intro: [20, 24], reveal: [24, 28],
  decode: [28, 40], karaoke: [40, 48], numbers: [48, 56], phone: [56, 63], outro: [63, 72] } as const;
export const TOTAL = b(72);
// where voices play (absolute frames): the score ducks under them
const VOICES = [[b(10) + 6, b(17)], [b(28.5), b(40)], [b(40.5), b(48)], [b(56) + 6, b(63)]];

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const useL = () => { const { width, height } = useVideoConfig(); const tall = height > width;
  return { tall, u: Math.min(width, height) / 1080, width, height }; };
export const pop = (f: number, at: number, damping = 12) => spring({ frame: f - at, fps: FPS, config: { damping, mass: 0.6 } });
export const Center: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) =>
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", ...style }}>{children}</AbsoluteFill>;
export const Sfx: React.FC<{ at: number; v?: number; src?: string }> = ({ at, v = 0.25, src = "tick.wav" }) =>
  <Sequence from={at} durationInFrames={8} layout="none"><Audio src={staticFile(src)} volume={v} /></Sequence>;

/* atmosphere: ember glow that breathes with the beat, film grain, vignette */
export const Backdrop: React.FC<{ heat: number }> = ({ heat }) => {
  const f = useCurrentFrame(), { width, height } = useVideoConfig();
  const pulse = 1 + 0.04 * Math.exp(-((f % BT) / 5));
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{ opacity: heat, background: `radial-gradient(${width * 0.95 * pulse}px ${height * 0.6 * pulse}px at 50% 42%, #3a2210 0%, transparent 70%)` }} />
      <AbsoluteFill style={{ opacity: 0.08, mixBlendMode: "screen" }}>
        <svg width="100%" height="100%"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={f % 9} /></filter>
          <rect width="100%" height="100%" filter="url(#g)" /></svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, #000000aa 100%)" }} />
    </AbsoluteFill>
  );
};

/* Thetha's orb; level per bar (0..1), or a gentle breath */
export const Orb: React.FC<{ size: number; level?: (i: number) => number; burst?: number }> = ({ size, level, burst = 0 }) => {
  const f = useCurrentFrame(), N = 84, c = size / 2, r0 = size * 0.235;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        {burst > 0 && burst < 1 && <circle cx={c} cy={c} r={r0 + burst * size * 0.9} fill="none" stroke={C.glow}
          strokeWidth={size * 0.02 * (1 - burst)} opacity={1 - burst} />}
        {Array.from({ length: N }, (_, i) => {
          const v = level ? level(i) : 0.06 + 0.04 * Math.sin(f / 27 + i * 0.3);
          const a = (i / N) * Math.PI * 2 - Math.PI / 2, len = 6 + v * size * 0.2;
          return <line key={i} x1={c + Math.cos(a) * r0} y1={c + Math.sin(a) * r0} x2={c + Math.cos(a) * (r0 + len)} y2={c + Math.sin(a) * (r0 + len)}
            stroke={`rgba(255,${150 + v * 60 | 0},${80 + v * 40 | 0},${0.25 + v * 0.75})`} strokeWidth={size / 125} strokeLinecap="round" />;
        })}
      </svg>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: size * 0.39, height: size * 0.39, transform: "translate(-50%,-50%)",
        borderRadius: "50%", background: `radial-gradient(circle at 36% 30%, ${C.glow}, ${C.ember} 58%, #a84a15)`,
        boxShadow: `0 ${size * 0.07}px ${size * 0.22}px -${size * 0.05}px #e2732bdd` }}>
        <div style={{ position: "absolute", left: "50%", top: "50%", width: size * 0.113, height: size * 0.113, transform: "translate(-50%,-50%)",
          borderRadius: "50%", background: "#1a0e05" }} />
      </div>
    </div>
  );
};

export const Mono: React.FC<{ children: React.ReactNode; u: number; color?: string; size?: number; style?: React.CSSProperties }> =
  ({ children, u, color = C.soft, size = 30, style }) =>
    <div style={{ fontFamily: mono, fontSize: size * u, letterSpacing: "0.16em", textTransform: "uppercase", color, ...style }}>{children}</div>;

/* ---------- A · cold open: the three click letters ---------- */
const Open: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL();
  const out = interpolate(f, [b(3.7), b(4)], [1, 0], clamp);
  return (
    <Center style={{ opacity: out }}>
      <div style={{ display: "flex", gap: (tall ? 40 : 90) * u, alignItems: "baseline" }}>
        {["c", "q", "x"].map((l, i) => { const p = pop(f, b(i + 1), 9);
          return <div key={l} style={{ fontFamily: grot, fontSize: (tall ? 330 : 380) * u, lineHeight: 1, color: i === 2 ? C.glow : C.ink,
            opacity: f >= b(i + 1) ? 1 : 0, transform: `scale(${1.8 - 0.8 * p}) rotate(${(1 - p) * (i - 1) * 12}deg)`,
            filter: `blur(${(1 - p) * 14}px)` }}>{l}</div>; })}
      </div>
      <Mono u={u} style={{ marginTop: 40 * u, opacity: interpolate(f, [b(3), b(3.4)], [0, 1], clamp) }}>the clicks of isiXhosa</Mono>
    </Center>
  );
};

/* ---------- B · Whisper's languages spin and land on the one it lacks ---------- */
const LANGS = ["English", "Kiswahili", "Español", "日本語", "Yorùbá", "Français", "العربية", "chiShona", "Deutsch", "हिन्दी",
  "Afrikaans", "Русский", "Hausa", "中文", "Português", "Soomaali", "한국어", "Lingála", "Türkçe", "አማርኛ", "Italiano",
  "Malagasy", "Ελληνικά", "Tiếng Việt", "Nederlands", "Polski", "isiXhosa"];
const reelPos = (f: number) => interpolate(f, [4, b(4.6)], [0, LANGS.length - 1], { ...clamp, easing: Easing.out(Easing.cubic) });
const Reel: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL(), len = b(6);
  const p = reelPos(f), i = Math.floor(p), frac = p - i, landed = p >= LANGS.length - 1, speed = p - reelPos(f - 1);
  const after = f - b(4.7), shake = landed && after > 0 && after < 14 ? Math.sin(after * 2.6) * (14 - after) * 1.6 * u : 0;
  const strike = interpolate(after, [6, 16], [0, 1], clamp), lineH = (tall ? 170 : 160) * u;
  const ticks: number[] = []; for (let k = 1; k < 80; k++) { if (Math.floor(reelPos(k)) !== Math.floor(reelPos(k - 1))) ticks.push(k); }
  return (
    <Center style={{ opacity: interpolate(f, [0, 6, len - 6, len], [0, 1, 1, 0], clamp), gap: 30 * u }}>
      {ticks.map(k => <Sfx key={k} at={k} v={0.22} />)}
      <Sfx at={b(4.7)} v={0.7} src="glitch.wav" />
      <div style={{ fontFamily: serif, color: C.ink, fontSize: (tall ? 78 : 80) * u, opacity: pop(f, 2, 200) }}>
        Whisper speaks <i style={{ color: C.glow }}>99</i> languages.</div>
      <div style={{ position: "relative", height: lineH * 4.2, width: "100%", overflow: "hidden",
        maskImage: "linear-gradient(transparent, #000 35%, #000 65%, transparent)", WebkitMaskImage: "linear-gradient(transparent, #000 35%, #000 65%, transparent)" }}>
        {[-2, -1, 0, 1, 2].map(k => { const name = LANGS[i + k]; if (!name) return null;
          const y = (k - frac) * lineH, me = k === 0 && landed;
          return <div key={i + k} style={{ position: "absolute", left: 0, right: 0, top: "50%", textAlign: "center",
            transform: `translate(${me ? shake : 0}px, ${y - lineH / 2}px)`, height: lineH, lineHeight: `${lineH}px`,
            fontFamily: grot, fontSize: (tall ? 140 : 150) * u, color: me ? C.err : k === 0 ? C.ink : C.soft, opacity: Math.max(0, 1 - Math.abs(y) / (lineH * 2.6)),
            filter: `blur(${Math.min(6, speed * 9)}px)` }}>
            <span style={{ position: "relative" }}>{name}
              {me && <span style={{ position: "absolute", left: -10 * u, top: "52%", height: 10 * u, width: `calc(${strike * 100}% + ${20 * u * strike}px)`,
                background: C.err, borderRadius: 99 }} />}</span></div>; })}
      </div>
      <div style={{ fontFamily: serif, fontStyle: "italic", color: C.err, fontSize: (tall ? 70 : 72) * u, opacity: interpolate(after, [12, 20], [0, 1], clamp) }}>
        …not this one.</div>
    </Center>
  );
};

/* ---------- C · what stock Whisper does with isiXhosa: the loop takes over the screen ---------- */
const Flood: React.FC = () => {
  const f = useCurrentFrame(), { tall, u, width, height } = useL(), clip = clips.loop, len = b(7);
  const real = clip.stock.replace(/(kwa )+kw?a?.*$/i, "").trim();
  const t0 = 6 + clip.speech_start * FPS;
  const shown = real.slice(0, Math.round(interpolate(f, [t0, t0 + 45], [0, real.length], clamp)));
  const n = Math.floor(interpolate(f, [t0 + 50, len - 12], [0, 140], { ...clamp, easing: Easing.in(Easing.cubic) }));
  const shake = n > 60 ? (random(`s${f}`) - 0.5) * n * 0.3 * u : 0;
  return (
    <AbsoluteFill style={{ opacity: f > len - 5 ? 0 : interpolate(f, [0, 6], [0, 1], clamp), transform: `translate(${shake}px, ${shake * 0.6}px)` }}>
      <Sequence from={6} layout="none"><Audio src={staticFile("loop.wav")} /></Sequence>
      {Array.from({ length: 11 }, (_, k) => <Sfx key={k} at={Math.round(interpolate(k, [0, 10], [t0 + 60, len - 10]))} v={0.18} src="glitch.wav" />)}
      {Array.from({ length: n }, (_, k) => {
        const x = random(`x${k}`) * width, y = random(`y${k}`) * height, s = (0.4 + random(`z${k}`) * 1.6) * (tall ? 90 : 80) * u;
        return <div key={k} style={{ position: "absolute", left: x - s, top: y - s / 2, fontFamily: grot, fontSize: s, color: random(`c${k}`) > 0.6 ? C.err : "#5e564acc",
          transform: `rotate(${(random(`r${k}`) - 0.5) * 30}deg)` }}>kwa</div>;
      })}
      <Center style={{ padding: 80 * u }}>
       <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30 * u, background: "#0c0a08e6", borderRadius: 28 * u,
         padding: `${40 * u}px ${50 * u}px`, boxShadow: `0 0 ${80 * u}px ${40 * u}px #0c0a08cc` }}>
        <Mono u={u} color={C.err}>stock Whisper hears isiXhosa</Mono>
        <div style={{ fontFamily: grot, fontSize: (tall ? 130 : 120) * u, lineHeight: 1, color: C.ink, textAlign: "center",
          textShadow: "0 0 40px #000, 0 0 80px #000" }}>{shown}{shown.length < real.length ? "▍" : ""}</div>
        <div style={{ fontFamily: mono, fontSize: 30 * u, color: C.soft, background: "#0c0a08cc", padding: `${8 * u}px ${18 * u}px`,
          opacity: interpolate(n, [20, 40], [0, 1], clamp) }}>…then it gets stuck: kwa kwa kwa kwa</div>
       </div>
      </Center>
    </AbsoluteFill>
  );
};

/* ---------- D · "So I taught it." one word per half-beat ---------- */
const Taught: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL();
  const words = ["So", "I", "taught", "it."];
  const k = Math.min(3, Math.floor(f / b(0.5))), p = pop(f, k * b(0.5), 10);
  return (
    <Center>
      <div style={{ fontFamily: grot, fontSize: (tall ? (k === 2 ? 260 : 380) : 360) * u, lineHeight: 1, color: k === 2 ? C.glow : C.ink,
        transform: `scale(${1.35 - 0.35 * p})`, opacity: interpolate(f, [b(3) - 4, b(3)], [1, 0], clamp) }}>{words[k]}</div>
    </Center>
  );
};

/* ---------- E · INTRODUCING ---------- */
const Intro: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL(), word = "INTRODUCING";
  const track = interpolate(f, [0, b(4)], [0.9, 0.3], { ...clamp, easing: Easing.out(Easing.quad) });
  return (
    <Center style={{ transform: `scale(${interpolate(f, [0, b(4)], [1, 1.12], clamp)})` }}>
      <div style={{ display: "flex", fontFamily: grot, fontSize: (tall ? 56 : 96) * u, color: C.ink, letterSpacing: `${track}em`, marginRight: `-${track}em` }}>
        {word.split("").map((ch, i) => { const o = interpolate(f, [i * 3, i * 3 + 8], [0, 1], clamp);
          return <span key={i} style={{ opacity: o, transform: `translateY(${(1 - o) * 40 * u}px)`, display: "inline-block" }}>{ch}</span>; })}
      </div>
      <div style={{ width: interpolate(f, [b(1), b(4)], [0, (tall ? 700 : 1100) * u], clamp), height: 3 * u, background: C.ember, marginTop: 40 * u,
        boxShadow: `0 0 ${30 * u}px ${C.ember}` }} />
    </Center>
  );
};

/* ---------- F · the reveal ---------- */
const Reveal: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL();
  const orb = pop(f, 2, 11), word = pop(f, 10, 14);
  return (
    <AbsoluteFill>
      <Center style={{ flexDirection: tall ? "column" : "row", gap: (tall ? 10 : 60) * u }}>
        <div style={{ transform: `scale(${orb})` }}><Orb size={(tall ? 520 : 480) * u} burst={interpolate(f, [2, 40], [0, 1], clamp)} /></div>
        <div style={{ textAlign: tall ? "center" : "left" }}>
          <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: (tall ? 260 : 280) * u, lineHeight: 0.95, color: C.ink,
            transform: `translateY(${(1 - word) * 60 * u}px)`, opacity: word }}>Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
          <Mono u={u} size={30} style={{ marginTop: 20 * u, opacity: interpolate(f, [24, 36], [0, 1], clamp) }}>isiXhosa for “speak”</Mono>
        </div>
      </Center>
      <AbsoluteFill style={{ background: "#fff3e0", opacity: interpolate(f, [0, 10], [1, 0], clamp), mixBlendMode: "screen" }} />
    </AbsoluteFill>
  );
};

/* ---------- G · you speak, Thetha writes: scrambled letters resolve in time with the voice ---------- */
const ABC = "abcdefghijklmnopqrstuvwxyz";
export const scramble = (w: string, f: number, k: number) => w.split("").map((_, i) => ABC[Math.floor(random(`${k}-${i}-${Math.floor(f / 2)}`) * 26)]).join("");
const Decode: React.FC = () => {
  const f = useCurrentFrame(), { tall, u, width } = useL(), clip = clips.loop, len = b(12), lead = b(0.5);
  const words = clip.r0012.split(" ");
  const s0 = lead + clip.speech_start * FPS, s1 = lead + clip.speech_end * FPS;
  const at = (k: number) => s0 + ((k + 1) / words.length) * (s1 - s0);        // word k resolves
  const appear = (k: number) => s0 + (k / words.length) * (s1 - s0) - 8;      // and starts scrambling a little before
  const done = f > s1 + 8, ok = pop(f, s1 + 10, 13);
  const heard = Math.max(0, (f - lead) / FPS) / clip.seconds, bars = clip.bars;
  return (
    <AbsoluteFill style={{ opacity: interpolate(f, [0, 8, len - 8, len], [0, 1, 1, 0], clamp) }}>
      <Sequence from={lead} layout="none"><Audio src={staticFile("loop.wav")} /></Sequence>
      {words.map((_, k) => <Sfx key={k} at={Math.round(at(k))} v={0.3} />)}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 0.35 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 * u, width: width * 0.92, height: (tall ? 900 : 600) * u }}>
          {Array.from({ length: 120 }, (_, i) => { const v = bars[Math.floor((i / 120) * bars.length)] || 0, on = i / 120 <= heard;
            return <div key={i} style={{ flex: 1, height: `${Math.max(2, v * 100)}%`, borderRadius: 99, background: on ? C.ember : C.line }} />; })}
        </div>
      </AbsoluteFill>
      <Center style={{ padding: (tall ? 80 : 140) * u, gap: 36 * u, alignItems: "flex-start" }}>
        <Mono u={u} color={C.glow}>you speak · Thetha writes</Mono>
        <div style={{ display: "flex", flexWrap: "wrap", gap: `${10 * u}px ${30 * u}px`, fontFamily: serif, fontSize: (tall ? 118 : 128) * u, lineHeight: 1.05 }}>
          {words.map((w, k) => { if (f < appear(k)) return null; const res = f >= at(k), p = pop(f, at(k), 12);
            return <span key={k} style={{ color: res ? C.ink : "#e2732b88", transform: `scale(${res ? 1.12 - 0.12 * p : 1})`, display: "inline-block",
              textShadow: res ? `0 0 ${40 * u * (1 - p)}px ${C.glow}` : "none" }}>{res ? w : scramble(w, f, k)}</span>; })}
        </div>
        <div style={{ fontFamily: mono, fontSize: 30 * u, color: C.ok, opacity: done ? ok : 0, transform: `translateY(${(1 - ok) * 20 * u}px)` }}>
          ✓ word for word · a sentence it never heard in training</div>
      </Center>
    </AbsoluteFill>
  );
};

/* ---------- H · lyric-style: one word at a time, huge ---------- */
const Karaoke: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL(), clip = clips.east, len = b(8), lead = b(0.5);
  const words = clip.r0012.split(" ");
  const s0 = lead + clip.speech_start * FPS, s1 = lead + clip.speech_end * FPS;
  const k = Math.max(-1, Math.min(words.length - 1, Math.floor(((f - s0) / (s1 - s0)) * words.length)));
  const p = pop(f, s0 + (k / words.length) * (s1 - s0), 11), after = f > s1 + 4;
  return (
    <AbsoluteFill style={{ opacity: interpolate(f, [0, 6, len - 6, len], [0, 1, 1, 0], clamp) }}>
      <Sequence from={lead} layout="none"><Audio src={staticFile("east.wav")} /></Sequence>
      <Center style={{ padding: 70 * u }}>
        {!after && k >= 0 && <div style={{ fontFamily: grot, fontSize: (tall ? Math.min(220, 1700 / words[k].length) : 230) * u, lineHeight: 1, color: C.ink,
          transform: `scale(${1.25 - 0.25 * p}) translateY(${(1 - p) * 30}px)`, textAlign: "center" }}>{words[k]}</div>}
        {after && <div style={{ fontFamily: serif, fontSize: (tall ? 104 : 96) * u, lineHeight: 1.08, color: C.ink, textAlign: "center",
          opacity: pop(f, s1 + 4, 200), maxWidth: (tall ? 940 : 1500) * u }}>{clip.r0012}</div>}
        <Mono u={u} color={C.faint} style={{ position: "absolute", bottom: (tall ? 260 : 120) * u, opacity: after ? 1 : 0.6 }}>
          {after ? "✓ exact · Google FLEURS test sentence" : "listening"}</Mono>
      </Center>
    </AbsoluteFill>
  );
};

/* ---------- I · the numbers, on the beat ---------- */
const Numbers: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL(), n = data.numbers;
  const swap = f >= b(2), p = pop(f, swap ? b(2) : 0, 10);
  const chips = [`${n.hours_of_speech} hours of open speech`, `~$${n.cost_usd} of cloud GPU`, "every experiment public"];
  return (
    <Center style={{ gap: 20 * u, opacity: interpolate(f, [b(8) - 6, b(8)], [1, 0], clamp) }}>
      <Mono u={u}>letters wrong on sentences it never heard</Mono>
      <div style={{ display: "flex", alignItems: "baseline", gap: 30 * u }}>
        <Mono u={u} color={swap ? C.ok : C.err} size={34}>{swap ? "after" : "before"}</Mono>
        <div style={{ fontFamily: grot, fontSize: (tall ? 400 : 380) * u, lineHeight: 1, color: swap ? C.glow : C.err,
          transform: `scale(${1.3 - 0.3 * p})`, fontVariantNumeric: "tabular-nums" }}>
          {swap ? n.r0012_fleurs_cer.toFixed(0) : n.stock_small_fleurs_cer.toFixed(0)}<span style={{ fontSize: (tall ? 180 : 170) * u }}>%</span></div>
      </div>
      <Mono u={u} color={C.faint} size={24} style={{ textTransform: "none", letterSpacing: "0.04em" }}>
        stock whisper-small 65.5 % → R-0012 8.0 % · FLEURS test, 1 034 clips</Mono>
      <div style={{ display: "flex", flexDirection: tall ? "column" : "row", alignItems: "center", gap: 18 * u, marginTop: 40 * u }}>
        {chips.map((c, i) => { const q = pop(f, b(4 + i), 12);
          return <div key={c} style={{ fontFamily: grot, fontSize: (tall ? 52 : 46) * u, color: C.ink, opacity: q, transform: `scale(${0.6 + 0.4 * q})`,
            border: `${3 * u}px solid ${C.ember}`, borderRadius: 99, padding: `${10 * u}px ${34 * u}px`, background: "#e2732b1c" }}>{c}</div>; })}
      </div>
    </Center>
  );
};

/* ---------- J · the phone, tilting in ---------- */
const Phone: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL(), clip = clips.train, lead = 6, len = b(7);
  const ph = (tall ? 1080 : 860) * u, pw = ph * 0.49, enter = pop(f, 0, 20);
  const s0 = lead + clip.speech_start * FPS, s1 = lead + clip.speech_end * FPS;
  const text = clip.r0012.slice(0, Math.round(interpolate(f, [s0, s1], [0, clip.r0012.length], clamp)));
  const k = Math.floor(((f - lead) / FPS) * 50);
  const level = (i: number) => (f > lead && f < lead + clip.seconds * FPS ? (clip.bars[Math.min(clip.bars.length - 1, k + (i % 7))] || 0) ** 1.3
    : 0.06 + 0.05 * Math.exp(-((f % BT) / 4)));
  const caption = (
    <div style={{ textAlign: tall ? "center" : "left", maxWidth: (tall ? 940 : 760) * u }}>
      <div style={{ fontFamily: grot, fontSize: (tall ? 84 : 92) * u, lineHeight: 1, color: C.ink, opacity: pop(f, 6, 200) }}>Runs in your browser.</div>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: (tall ? 76 : 80) * u, lineHeight: 1.05, color: C.glow, marginTop: 16 * u,
        opacity: pop(f, b(1), 200) }}>Nothing you say leaves your phone.</div>
      <Mono u={u} color={C.faint} size={24} style={{ marginTop: 26 * u, opacity: pop(f, b(2), 200) }}>
        free · no account · ~{data.numbers.browser_mb} mb once</Mono>
    </div>
  );
  return (
    <AbsoluteFill style={{ opacity: interpolate(f, [len - 6, len], [1, 0], clamp) }}>
      <Sequence from={lead} layout="none"><Audio src={staticFile("train.wav")} /></Sequence>
      <Center style={{ flexDirection: tall ? "column" : "row", gap: 70 * u, perspective: 2200 }}>
        {!tall && caption}
        <div style={{ width: pw, height: ph, borderRadius: pw * 0.13, border: `${6 * u}px solid #2f2820`, background: C.bg, position: "relative", overflow: "hidden",
          boxShadow: `0 ${50 * u}px ${140 * u}px -${30 * u}px #000, 0 0 ${120 * u}px #e2732b33`,
          transform: `rotateY(${interpolate(enter, [0, 1], [-50, tall ? -8 : -16])}deg) rotateX(${interpolate(enter, [0, 1], [20, 6])}deg) translateY(${(1 - enter) * 300 * u}px)` }}>
          <AbsoluteFill style={{ background: "radial-gradient(120% 60% at 50% 30%, #2c1d10 0%, transparent 70%)" }} />
          <div style={{ position: "absolute", top: ph * 0.04, left: pw * 0.08, fontFamily: serif, fontStyle: "italic", fontSize: pw * 0.085, color: C.ink }}>
            Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
          <div style={{ position: "absolute", top: ph * 0.17, left: "50%", transform: "translateX(-50%)" }}><Orb size={pw * 0.8} level={level} /></div>
          <div style={{ position: "absolute", top: ph * 0.6, left: pw * 0.08, right: pw * 0.08, fontFamily: serif, fontSize: pw * 0.088, lineHeight: 1.12, color: C.ink }}>{text}</div>
        </div>
        {tall && caption}
      </Center>
    </AbsoluteFill>
  );
};

/* ---------- K · the end card ---------- */
const Outro: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useL();
  const s = pop(f, 0, 12), line = (d: number) => pop(f, d, 200);
  const level = (i: number) => 0.08 + 0.3 * Math.exp(-((f % BT) / 5)) * (0.5 + 0.5 * Math.sin(i * 0.9 + f / 9));
  return (
    <Center style={{ gap: 20 * u, padding: 60 * u, opacity: interpolate(f, [b(9) - 14, b(9)], [1, 0], clamp) }}>
      <div style={{ transform: `scale(${s})` }}><Orb size={(tall ? 360 : 280) * u} level={level} /></div>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: (tall ? 240 : 220) * u, lineHeight: 0.95, color: C.ink, opacity: s }}>
        Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
      <div style={{ fontFamily: grot, fontSize: (tall ? 58 : 52) * u, color: C.ink, opacity: line(8), textAlign: "center" }}>
        Speak isiXhosa. <span style={{ color: C.glow }}>See it written.</span></div>
      <div style={{ fontFamily: mono, fontSize: (tall ? 34 : 38) * u, color: C.bg, background: C.glow, padding: `${12 * u}px ${26 * u}px`, borderRadius: 12 * u,
        marginTop: 20 * u, opacity: line(16), transform: `scale(${0.9 + 0.1 * line(16)})` }}>ntlakanipho-thetha.static.hf.space</div>
      <div style={{ fontFamily: mono, fontSize: 26 * u, color: C.soft, opacity: line(24), textAlign: "center" }}>
        open source · github.com/2Ntlaks/isixhosa-speech-ai</div>
      <div style={{ fontFamily: mono, fontSize: 22 * u, color: C.faint, opacity: line(34), marginTop: 30 * u, textAlign: "center", lineHeight: 1.6 }}>
        built by Ntlakanipho Mgaguli<br />voices: Google FLEURS (CC BY 4.0) · trained on NCHLT (SADiLaR) + FLEURS</div>
    </Center>
  );
};

/* ---------- the film ---------- */
const SCENES: [keyof typeof SEC, React.FC][] = [["open", Open], ["reel", Reel], ["flood", Flood], ["taught", Taught], ["intro", Intro],
  ["reveal", Reveal], ["decode", Decode], ["karaoke", Karaoke], ["numbers", Numbers], ["phone", Phone], ["outro", Outro]];

export const Video: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Backdrop heat={f < b(24) ? 0.35 : 1} />
      <Audio src={staticFile("music.wav")} volume={(fr) => (VOICES.some(([a, z]) => fr >= a && fr < z) ? 0.32 : 0.9)} />
      {SCENES.map(([k, S]) => (
        <Sequence key={k} from={b(SEC[k][0])} durationInFrames={b(SEC[k][1] - SEC[k][0])}><S /></Sequence>))}
    </AbsoluteFill>
  );
};
