// TikTok cut: ~19 s, hook in the first second, caption-style text inside TikTok's safe area
// (clear of the top bar, the right-hand buttons and the bottom caption). Same real transcripts as the main film.
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, random, staticFile, useCurrentFrame } from "remotion";
import { Backdrop, C, Center, FPS, Orb, Sfx, b, clamp, clips, grot, mono, pop, scramble, serif } from "./Video";

export const TT_TOTAL = b(32);
const SAFE: React.CSSProperties = { position: "absolute", left: 70, right: 160, top: 250, bottom: 520 };  // TikTok UI-free zone
const VOICES = [[3, b(8)], [b(10.5), b(20)]];

/* a TikTok-style caption: white bold type on a dark rounded box */
const Cap: React.FC<{ children: React.ReactNode; show: number; size?: number; color?: string }> = ({ children, show, size = 64, color = C.ink }) => (
  <div style={{ display: "inline-block", fontFamily: grot, fontSize: size, lineHeight: 1.1, color, background: "#0c0a08e0", borderRadius: 18,
    padding: "14px 26px", opacity: show, transform: `scale(${0.85 + 0.15 * show})`, transformOrigin: "left center" }}>{children}</div>
);

/* 0-8 beats: the hook. AI meets isiXhosa and loops. */
const Hook: React.FC = () => {
  const f = useCurrentFrame(), clip = clips.loop;
  const real = clip.stock.replace(/(kwa )+kw?a?.*$/i, "").trim();
  const t0 = 3 + clip.speech_start * FPS;
  const shown = real.slice(0, Math.round(interpolate(f, [t0, t0 + 30], [0, real.length], clamp)));
  const n = Math.floor(interpolate(f, [t0 + 28, b(8) - 4], [0, 120], { ...clamp, easing: Easing.in(Easing.quad) }));
  const shake = n > 50 ? (random(`s${f}`) - 0.5) * n * 0.35 : 0;
  return (
    <AbsoluteFill style={{ opacity: f > b(8) - 3 ? 0 : 1 }}>
      <Sequence from={3} layout="none"><Audio src={staticFile("loop.wav")} /></Sequence>
      {Array.from({ length: 8 }, (_, k) => <Sfx key={k} at={Math.round(interpolate(k, [0, 7], [t0 + 34, b(8) - 6]))} v={0.18} src="glitch.wav" />)}
      <AbsoluteFill style={{ transform: `translate(${shake}px, ${shake * 0.6}px)` }}>
        {Array.from({ length: n }, (_, k) => { const s = (0.5 + random(`z${k}`) * 1.5) * 80;
          return <div key={k} style={{ position: "absolute", left: random(`x${k}`) * 1080 - s, top: random(`y${k}`) * 1920 - s / 2, fontFamily: grot, fontSize: s,
            color: random(`c${k}`) > 0.55 ? C.err : "#5e564acc", transform: `rotate(${(random(`r${k}`) - 0.5) * 34}deg)` }}>kwa</div>; })}
      </AbsoluteFill>
      <div style={{ ...SAFE, display: "flex", flexDirection: "column", gap: 26 }}>
        <Cap show={pop(f, 0, 200)} size={66}>I asked AI to write down isiXhosa…</Cap>
        <div style={{ fontFamily: grot, fontSize: 120, lineHeight: 1, color: C.ink, marginTop: 60, textShadow: "0 0 40px #000, 0 0 90px #000" }}>
          {shown}{shown.length < real.length ? "▍" : ""}</div>
        <div style={{ marginTop: "auto" }}><Cap show={pop(f, b(5), 12)} size={72} color={C.err}>it got stuck 💀</Cap></div>
      </div>
    </AbsoluteFill>
  );
};

/* 8-10 beats: the turn */
const Turn: React.FC = () => {
  const f = useCurrentFrame(), p = pop(f, 0, 10);
  return (
    <Center>
      <AbsoluteFill style={{ background: "#fff3e0", opacity: interpolate(f, [0, 8], [0.9, 0], clamp), mixBlendMode: "screen" }} />
      <div style={{ fontFamily: grot, fontSize: 132, lineHeight: 1.02, color: C.ink, textAlign: "center", transform: `scale(${1.3 - 0.3 * p})`, padding: "0 90px" }}>
        so I trained<br /><span style={{ color: C.glow }}>my own.</span></div>
    </Center>
  );
};

/* 10-20 beats: same voice, scrambled letters resolve into the exact sentence */
const Fix: React.FC = () => {
  const f = useCurrentFrame(), clip = clips.loop, lead = b(0.5);
  const words = clip.r0012.split(" ");
  const s0 = lead + clip.speech_start * FPS, s1 = lead + clip.speech_end * FPS;
  const at = (k: number) => s0 + ((k + 1) / words.length) * (s1 - s0);
  const done = f > s1 + 4, ok = pop(f, s1 + 6, 12);
  return (
    <AbsoluteFill>
      <Sequence from={lead} layout="none"><Audio src={staticFile("loop.wav")} /></Sequence>
      {words.map((_, k) => <Sfx key={k} at={Math.round(at(k))} v={0.3} />)}
      <div style={{ ...SAFE, display: "flex", flexDirection: "column", gap: 40 }}>
        <Cap show={pop(f, 0, 200)} size={60}>same voice. my model:</Cap>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 26px", fontFamily: serif, fontSize: 118, lineHeight: 1.04, marginTop: 40 }}>
          {words.map((w, k) => { if (f < s0 + (k / words.length) * (s1 - s0) - 8) return null; const res = f >= at(k), p = pop(f, at(k), 12);
            return <span key={k} style={{ color: res ? C.ink : "#e2732b88", display: "inline-block", transform: `scale(${res ? 1.12 - 0.12 * p : 1})`,
              textShadow: res ? `0 0 ${40 * (1 - p)}px ${C.glow}` : "none" }}>{res ? w : scramble(w, f, k)}</span>; })}
        </div>
        <div style={{ marginTop: "auto", opacity: done ? 1 : 0 }}><Cap show={ok} size={72} color={C.ok}>every word ✓</Cap></div>
      </div>
    </AbsoluteFill>
  );
};

/* 20-25 beats: three punches */
const Punch: React.FC = () => {
  const f = useCurrentFrame();
  const items: [number, React.ReactNode][] = [[0, <><span style={{ color: C.glow }}>8%</span> errors</>], [b(1.5), <>~$10 to train</>],
    [b(3), <>free, on <span style={{ color: C.glow }}>your phone</span></>]];
  return (
    <div style={{ ...SAFE, display: "flex", flexDirection: "column", justifyContent: "center", gap: 34 }}>
      {items.map(([at, t], i) => { const p = pop(f, at, 11);
        return <div key={i} style={{ fontFamily: grot, fontSize: 116, lineHeight: 1, color: C.ink, opacity: f >= at ? 1 : 0,
          transform: `translateX(${(1 - p) * -120}px) scale(${1.2 - 0.2 * p})`, transformOrigin: "left center" }}>{t}</div>; })}
    </div>
  );
};

/* 25-32 beats: the product */
const Product: React.FC = () => {
  const f = useCurrentFrame(), clip = clips.loop, enter = pop(f, 0, 18);
  const level = (i: number) => 0.08 + 0.35 * Math.exp(-((f % 18) / 5)) * (0.5 + 0.5 * Math.sin(i * 0.9 + f / 8));
  const ph = 860, pw = ph * 0.49;
  return (
    <AbsoluteFill>
      <div style={{ ...SAFE, display: "flex", flexDirection: "column", alignItems: "center", gap: 34, perspective: 2000 }}>
        <div style={{ width: pw, height: ph, borderRadius: pw * 0.13, border: "6px solid #2f2820", background: C.bg, position: "relative", overflow: "hidden",
          boxShadow: "0 50px 140px -30px #000, 0 0 120px #e2732b33",
          transform: `rotateY(${interpolate(enter, [0, 1], [-45, -8])}deg) rotateX(${interpolate(enter, [0, 1], [18, 5])}deg) translateY(${(1 - enter) * 260}px)` }}>
          <AbsoluteFill style={{ background: "radial-gradient(120% 60% at 50% 30%, #2c1d10 0%, transparent 70%)" }} />
          <div style={{ position: "absolute", top: ph * 0.04, left: pw * 0.08, fontFamily: serif, fontStyle: "italic", fontSize: pw * 0.085, color: C.ink }}>
            Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
          <div style={{ position: "absolute", top: ph * 0.17, left: "50%", transform: "translateX(-50%)" }}><Orb size={pw * 0.8} level={level} /></div>
          <div style={{ position: "absolute", top: ph * 0.6, left: pw * 0.08, right: pw * 0.08, fontFamily: serif, fontSize: pw * 0.08, lineHeight: 1.12, color: C.ink }}>
            {clip.r0012}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: 120, lineHeight: 1, color: C.ink, opacity: pop(f, 6, 200) }}>
            Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
          <div style={{ fontFamily: mono, fontSize: 30, letterSpacing: "0.14em", color: C.glow, marginTop: 14, opacity: pop(f, 14, 200) }}>
            SPEAK ISIXHOSA · LINK IN BIO</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const PARTS: [number, number, React.FC][] = [[0, 8, Hook], [8, 10, Turn], [10, 20, Fix], [20, 25, Punch], [25, 32, Product]];

export const TikTok: React.FC<{ music: boolean }> = ({ music }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Backdrop heat={f < b(10) ? 0.4 : 1} />
      {music && <Audio src={staticFile("music_tiktok.wav")} volume={(fr) => (VOICES.some(([a, z]) => fr >= a && fr < z) ? 0.35 : 0.9)} />}
      {PARTS.map(([s, e, P], i) => <Sequence key={i} from={b(s)} durationInFrames={b(e - s)}><P /></Sequence>)}
    </AbsoluteFill>
  );
};
