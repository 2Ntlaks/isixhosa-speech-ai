// "Thetha" announcement film. Every transcript on screen comes from a run record (prepare.py -> data.json).
// Frame-driven animation only (interpolate/spring), so every render is identical.
import React from "react";
import {
  AbsoluteFill, Audio, Easing, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { loadFont as loadSerif } from "@remotion/google-fonts/InstrumentSerif";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import data from "./data.json";

const serif = loadSerif("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
loadSerif("italic", { weights: ["400"], subsets: ["latin"] });
const mono = loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily;

const C = { bg: "#100e0b", ink: "#f2e9d8", soft: "#a39883", faint: "#5e564a", line: "#2a241c",
  ember: "#e2732b", glow: "#ffb067", ok: "#6fd0a6", err: "#ff8a7a" };
const FPS = 30;
type Clip = (typeof data.clips)["loop"];
const clips = data.clips as Record<"loop" | "train" | "east", Clip>;

// scene lengths in frames (40 s at 30 fps)
const S = { hook: 120, loop: 225, fixed: 225, split: 195, numbers: 165, phone: 135, end: 135 };
const starts = (() => { let t = 0; const o: Record<string, number> = {};
  for (const [k, v] of Object.entries(S)) { o[k] = t; t += v; } return o; })();
export const TOTAL = Object.values(S).reduce((a, b) => a + b, 0);

/* helpers */
const useLayout = () => {
  const { width, height } = useVideoConfig();
  const tall = height > width;
  return { tall, u: Math.min(width, height) / 1080, width, height };  // u: one "unit" scales with the short side
};
const fadeInOut = (f: number, len: number, inF = 12, outF = 10) =>
  interpolate(f, [0, inF, len - outF, len], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const typed = (text: string, f: number, from: number, to: number) => {
  const p = interpolate(f, [from, to], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return text.slice(0, Math.round(p * text.length));
};

/* atmosphere: the Thetha glow, slowly breathing, with film grain */
const Backdrop: React.FC = () => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const drift = Math.sin(f / 70) * 4;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{ background: `radial-gradient(${width * 0.9}px ${height * 0.5}px at 50% ${30 + drift}%, #2c1d10 0%, transparent 70%)` }} />
      <AbsoluteFill style={{ opacity: 0.07, mixBlendMode: "screen" }}>
        <svg width="100%" height="100%">
          <filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={f % 12} /></filter>
          <rect width="100%" height="100%" filter="url(#g)" />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* the Thetha orb with its ring of bars; level drives the bars (0 = breathing) */
const Orb: React.FC<{ size: number; level?: number[] }> = ({ size, level }) => {
  const f = useCurrentFrame();
  const BARS = 84, c = size / 2, r0 = size * 0.235;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: BARS }, (_, i) => {
          const v = level ? level[i % level.length] : 0.06 + 0.04 * Math.sin(f / 27 + i * 0.3);
          const a = (i / BARS) * Math.PI * 2 - Math.PI / 2, len = 6 + v * size * 0.2;
          return <line key={i} x1={c + Math.cos(a) * r0} y1={c + Math.sin(a) * r0} x2={c + Math.cos(a) * (r0 + len)}
            y2={c + Math.sin(a) * (r0 + len)} stroke={`rgba(255,${150 + v * 60 | 0},${80 + v * 40 | 0},${0.25 + v * 0.75})`}
            strokeWidth={size / 125} strokeLinecap="round" />;
        })}
      </svg>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: size * 0.39, height: size * 0.39, marginLeft: -size * 0.195,
        marginTop: -size * 0.195, borderRadius: "50%", background: `radial-gradient(circle at 36% 30%, ${C.glow}, ${C.ember} 58%, #a84a15)`,
        boxShadow: `0 ${size * 0.07}px ${size * 0.2}px -${size * 0.06}px #e2732bcc` }}>
        <div style={{ position: "absolute", left: "50%", top: "50%", width: size * 0.113, height: size * 0.113,
          transform: "translate(-50%,-50%)", borderRadius: "50%", background: "#1a0e05" }} />
      </div>
    </div>
  );
};

/* the clip's loudness as bars; the part already heard glows */
const Wave: React.FC<{ clip: Clip; at: number; w: number; h: number }> = ({ clip, at, w, h }) => {
  const n = 96, bars = clip.bars, step = bars.length / n;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: w / n * 0.35, width: w, height: h }}>
      {Array.from({ length: n }, (_, i) => {
        const v = Math.max(...bars.slice(Math.floor(i * step), Math.floor((i + 1) * step) + 1));
        const heard = (i + 0.5) / n <= at / clip.seconds;
        return <div key={i} style={{ flex: 1, height: Math.max(h * 0.04, v * h), borderRadius: 99,
          background: heard ? C.glow : C.faint, opacity: heard ? 1 : 0.45 }} />;
      })}
    </div>
  );
};

const Label: React.FC<{ children: React.ReactNode; color?: string; u: number }> = ({ children, color = C.soft, u }) => (
  <div style={{ fontFamily: mono, fontSize: 30 * u, letterSpacing: "0.18em", textTransform: "uppercase", color }}>{children}</div>
);

/* ---------- scenes ---------- */

const Hook: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useLayout();
  const l1 = spring({ frame: f - 8, fps: FPS, config: { damping: 200 } });
  const l2 = spring({ frame: f - 48, fps: FPS, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: fadeInOut(f, S.hook, 8, 12),
      flexDirection: tall ? "column" : "row", gap: 60 * u, padding: 80 * u }}>
      <Orb size={(tall ? 420 : 360) * u} />
      <div style={{ fontFamily: serif, color: C.ink, fontSize: (tall ? 92 : 84) * u, lineHeight: 1.05, textAlign: tall ? "center" : "left", maxWidth: tall ? 900 * u : 1000 * u }}>
        <div style={{ opacity: l1, transform: `translateY(${(1 - l1) * 30}px)` }}>Whisper speaks 99 languages.</div>
        <div style={{ opacity: l2, transform: `translateY(${(1 - l2) * 30}px)`, marginTop: 18 * u, fontStyle: "italic" }}>
          <span style={{ color: C.glow }}>isiXhosa</span> isn't one of them.</div>
      </div>
    </AbsoluteFill>
  );
};

const Transcribe: React.FC<{ name: keyof typeof clips; mode: "stock" | "fixed"; len: number }> = ({ name, mode, len }) => {
  const clip = clips[name];
  const f = useCurrentFrame(), { tall, u, width } = useLayout();
  const lead = 12, t = (f - lead) / FPS;  // audio starts after a short beat
  const from = lead + clip.speech_start * FPS, to = lead + clip.speech_end * FPS;
  let text = mode === "fixed" ? typed(clip.r0012, f, from, to) : "";
  let flood = 0;
  if (mode === "stock") {  // the real output, then the loop keeps going, faster and faster
    const real = clip.stock.replace(/(kwa )+kw?a?.*$/i, "").trim();
    text = typed(real, f, from, from + (to - from) * 0.55);
    flood = Math.floor(interpolate(f, [from + (to - from) * 0.55, len - 18], [0, 70], { extrapolateLeft: "clamp", extrapolateRight: "clamp",
      easing: Easing.in(Easing.quad) }));
    if (flood) text += " " + Array(flood).fill("kwa").join(" ");
  }
  const done = mode === "fixed" && f > to + 6;
  const ok = spring({ frame: f - to - 6, fps: FPS, config: { damping: 14 } });
  const shake = mode === "stock" && flood > 40 ? Math.sin(f * 2.1) * (flood - 40) * 0.25 * u : 0;
  const fs = (tall ? 96 : 70) * u * (mode === "stock" ? interpolate(flood, [0, 70], [1, 0.62], { extrapolateRight: "clamp" }) : 1);
  return (
    <AbsoluteFill style={{ opacity: fadeInOut(f, len), padding: (tall ? 90 : 110) * u, justifyContent: "center", gap: 46 * u }}>
      <Sequence from={lead} layout="none"><Audio src={staticFile(name + ".wav")} /></Sequence>
      <Label u={u} color={mode === "stock" ? C.err : C.ok}>
        {mode === "stock" ? `${clip.stock_name} hears isiXhosa` : "after fine-tuning · R-0012"}
      </Label>
      <Wave clip={clip} at={Math.max(0, t)} w={width - 2 * (tall ? 90 : 110) * u} h={(tall ? 230 : 120) * u} />
      <div style={{ fontFamily: serif, fontSize: fs, lineHeight: 1.12, color: mode === "stock" ? C.err : C.ink, minHeight: 300 * u,
        transform: `translateX(${shake}px)`, overflowWrap: "anywhere", textShadow: mode === "fixed" ? `0 0 ${40 * u}px #e2732b33` : "none" }}>
        {text}<span style={{ color: C.ember, opacity: Math.floor(f / 8) % 2 && !done ? 1 : 0 }}>|</span>
      </div>
      <div style={{ fontFamily: mono, fontSize: (tall ? 32 : 28) * u, lineHeight: 1.4, color: done ? C.ok : C.faint, opacity: mode === "stock" ? interpolate(flood, [30, 45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : ok,
        transform: `scale(${mode === "fixed" ? 0.9 + ok * 0.1 : 1})`, transformOrigin: "left" }}>
        {mode === "stock" ? "…stuck in a loop. it never heard isiXhosa." : "✓ exactly what was said · a sentence it never heard in training"}
      </div>
    </AbsoluteFill>
  );
};

const Split: React.FC = () => {
  const f = useCurrentFrame(), { tall, u, width } = useLayout(), clip = clips.train, len = S.split;
  const lead = 10, from = lead + clip.speech_start * FPS, to = lead + clip.speech_end * FPS;
  const pad = (tall ? 90 : 110) * u;
  const row = (label: string, color: string, text: string, strike: boolean) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 * u }}>
      <Label u={u} color={color}>{label}</Label>
      <div style={{ fontFamily: serif, fontSize: (tall ? 80 : 58) * u, lineHeight: 1.12, color: strike ? C.faint : C.ink, minHeight: (tall ? 220 : 140) * u,
        textDecoration: strike && f > to + 4 ? `line-through ${C.err}` : "none", textDecorationThickness: 3 * u }}>{text}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ opacity: fadeInOut(f, len), padding: pad, justifyContent: "center", gap: 50 * u }}>
      <Sequence from={lead} layout="none"><Audio src={staticFile("train.wav")} /></Sequence>
      <Wave clip={clip} at={Math.max(0, (f - lead) / FPS)} w={width - 2 * pad} h={(tall ? 190 : 90) * u} />
      {row("stock whisper-medium", C.err, typed(clip.stock, f, from, to), true)}
      {row("R-0012", C.ok, typed(clip.r0012, f, from, to), false)}
    </AbsoluteFill>
  );
};

const Numbers: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useLayout(), len = S.numbers, n = data.numbers;
  const p = interpolate(f, [10, 75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const v = n.stock_small_fleurs_cer + (n.r0012_fleurs_cer - n.stock_small_fleurs_cer) * p;
  const chips = [`${n.hours_of_speech} h of open speech`, `~$${n.cost_usd} of cloud GPU`, "every experiment public"];
  return (
    <AbsoluteFill style={{ opacity: fadeInOut(f, len), alignItems: "center", justifyContent: "center", gap: 34 * u, padding: 80 * u }}>
      <Label u={u}>letters wrong on sentences it never heard</Label>
      <div style={{ fontFamily: serif, fontSize: (tall ? 330 : 300) * u, lineHeight: 0.9, color: p > 0.98 ? C.glow : C.ink, fontVariantNumeric: "tabular-nums" }}>
        {v.toFixed(1)}<span style={{ fontSize: (tall ? 150 : 130) * u }}>%</span></div>
      <div style={{ width: (tall ? 820 : 1100) * u, height: 14 * u, borderRadius: 99, background: C.line, overflow: "hidden" }}>
        <div style={{ width: `${v}%`, height: "100%", borderRadius: 99, background: `linear-gradient(90deg, ${C.glow}, ${C.ember})` }} />
      </div>
      <div style={{ fontFamily: mono, fontSize: 28 * u, color: C.faint, textAlign: "center" }}>stock whisper-small 65.5 % → R-0012 8.0 % · FLEURS test, 1 034 clips</div>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 18 * u, marginTop: 30 * u, maxWidth: (tall ? 900 : 1500) * u }}>
        {chips.map((c, i) => { const s = spring({ frame: f - 80 - i * 9, fps: FPS, config: { damping: 15 } });
          return <div key={c} style={{ fontFamily: mono, fontSize: 30 * u, color: C.ink, border: `${2 * u}px solid #e2732b66`, background: "#e2732b18",
            borderRadius: 99, padding: `${12 * u}px ${28 * u}px`, opacity: s, transform: `translateY(${(1 - s) * 20}px)` }}>{c}</div>; })}
      </div>
    </AbsoluteFill>
  );
};

const Phone: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useLayout(), len = S.phone, clip = clips.east;
  const ph = (tall ? 1150 : 820) * u, pw = ph * 0.49;
  const lift = spring({ frame: f, fps: FPS, config: { damping: 200 } });
  const level = Array.from({ length: 84 }, (_, i) => {
    const k = Math.floor(((f - 8) / FPS) * 50);
    const v = clip.bars[Math.max(0, Math.min(clip.bars.length - 1, k + (i % 6)))] || 0;
    return f > 8 && f < 8 + clip.seconds * FPS ? v ** 1.4 : 0.06 + 0.04 * Math.sin(f / 27 + i * 0.3);
  });
  const text = typed(clip.r0012, f, 8 + clip.speech_start * FPS, 8 + clip.speech_end * FPS);
  const caption = (
    <div style={{ fontFamily: serif, color: C.ink, fontSize: (tall ? 70 : 76) * u, lineHeight: 1.08, maxWidth: (tall ? 900 : 700) * u, textAlign: tall ? "center" : "left" }}>
      Runs in your browser.<div style={{ fontStyle: "italic", color: C.glow }}>Nothing you say leaves your phone.</div>
      <div style={{ fontFamily: mono, fontSize: 24 * u, color: C.faint, marginTop: 24 * u, lineHeight: 1.5 }}>
        ~{data.numbers.browser_mb} MB, downloaded once · free · no account</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ opacity: fadeInOut(f, len), alignItems: "center", justifyContent: "center", flexDirection: tall ? "column" : "row", gap: 70 * u }}>
      <Sequence from={8} layout="none"><Audio src={staticFile("east.wav")} /></Sequence>
      {!tall && caption}
      <div style={{ width: pw, height: ph, borderRadius: pw * 0.13, border: `${6 * u}px solid #2a241c`, background: C.bg, position: "relative", overflow: "hidden",
        boxShadow: `0 ${40 * u}px ${120 * u}px -${30 * u}px #000, 0 0 ${80 * u}px #e2732b22`, transform: `translateY(${(1 - lift) * 120 * u}px)` }}>
        <AbsoluteFill style={{ background: "radial-gradient(120% 60% at 50% 30%, #2c1d10 0%, transparent 70%)" }} />
        <div style={{ position: "absolute", top: ph * 0.04, left: pw * 0.08, fontFamily: serif, fontStyle: "italic", fontSize: pw * 0.085, color: C.ink }}>
          Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
        <div style={{ position: "absolute", top: ph * 0.2, left: "50%", transform: "translateX(-50%)" }}><Orb size={pw * 0.78} level={level} /></div>
        <div style={{ position: "absolute", top: ph * 0.62, left: pw * 0.08, right: pw * 0.08, fontFamily: serif, fontSize: pw * 0.085, lineHeight: 1.12, color: C.ink }}>{text}</div>
        <div style={{ position: "absolute", bottom: ph * 0.03, left: 0, right: 0, textAlign: "center", fontFamily: mono, fontSize: pw * 0.026, color: C.faint }}>
          nothing you record leaves this device</div>
      </div>
      {tall && caption}
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const f = useCurrentFrame(), { tall, u } = useLayout();
  const s = spring({ frame: f - 4, fps: FPS, config: { damping: 18 } });
  const line = (txt: string, d: number, size: number, color: string, font = mono) => {
    const o = spring({ frame: f - d, fps: FPS, config: { damping: 200 } });
    return <div style={{ fontFamily: font, fontSize: size * u, color, opacity: o, transform: `translateY(${(1 - o) * 16}px)`, textAlign: "center" }}>{txt}</div>;
  };
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 26 * u, padding: 70 * u,
      opacity: interpolate(f, [S.end - 14, S.end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: (tall ? 230 : 210) * u, color: C.ink, transform: `scale(${0.9 + s * 0.1})`, opacity: s }}>
        Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
      {line("speak isiXhosa · see it written", 14, 34, C.soft)}
      {line("ntlakanipho-thetha.static.hf.space", 26, tall ? 40 : 44, C.glow)}
      {line("open source · github.com/2Ntlaks/isixhosa-speech-ai", 38, 28, C.soft)}
      <div style={{ height: 40 * u }} />
      {line("built by Ntlakanipho Mgaguli", 50, 26, C.faint)}
      {line("speech in this film: Google FLEURS (CC BY 4.0)", 58, tall ? 24 : 22, C.faint)}
      {line("trained on NCHLT (SADiLaR) and Google FLEURS", 62, tall ? 24 : 22, C.faint)}
    </AbsoluteFill>
  );
};

/* ---------- the film ---------- */
const Ticks: React.FC<{ from: number; to: number; every: number }> = ({ from, to, every }) => (
  <>{Array.from({ length: Math.max(0, Math.floor((to - from) / every)) }, (_, i) =>
    <Sequence key={i} from={Math.round(from + i * every)} durationInFrames={4}><Audio src={staticFile("tick.wav")} volume={0.18} /></Sequence>)}</>
);

export const Video: React.FC = () => {
  const L = clips.loop, T = clips.train, E = clips.east;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Backdrop />
      <Audio src={staticFile("bed.wav")} volume={(f) => interpolate(f, [0, 30, TOTAL - 60, TOTAL], [0, 0.55, 0.55, 0], { extrapolateRight: "clamp" })} />
      {Object.entries(starts).slice(1).map(([k, s]) => (
        <Sequence key={k} from={s - 8} durationInFrames={30}><Audio src={staticFile("whoosh.wav")} volume={0.35} /></Sequence>))}
      <Sequence from={starts.hook} durationInFrames={S.hook}><Hook /></Sequence>
      <Sequence from={starts.loop} durationInFrames={S.loop}><Transcribe name="loop" mode="stock" len={S.loop} /></Sequence>
      <Sequence from={starts.fixed} durationInFrames={S.fixed}><Transcribe name="loop" mode="fixed" len={S.fixed} /></Sequence>
      <Ticks from={starts.fixed + 12 + L.speech_start * FPS} to={starts.fixed + 12 + L.speech_end * FPS} every={5} />
      <Sequence from={starts.split} durationInFrames={S.split}><Split /></Sequence>
      <Ticks from={starts.split + 10 + T.speech_start * FPS} to={starts.split + 10 + T.speech_end * FPS} every={6} />
      <Sequence from={starts.numbers} durationInFrames={S.numbers}><Numbers /></Sequence>
      <Sequence from={starts.phone} durationInFrames={S.phone}><Phone /></Sequence>
      <Ticks from={starts.phone + 8 + E.speech_start * FPS} to={starts.phone + 8 + E.speech_end * FPS} every={6} />
      <Sequence from={starts.end} durationInFrames={S.end}><End /></Sequence>
    </AbsoluteFill>
  );
};
