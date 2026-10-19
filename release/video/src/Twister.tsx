// TikTok: "Can AI keep up with an isiXhosa tongue twister?" The founder's own voice (D-0023) and the demo model's
// real output for it; his own words shown next to it. Plain language for a non-technical audience. 22 beats, 100 BPM.
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Backdrop, C, Center, FPS, Orb, Sfx, b, clamp, grot, mono, pop, serif } from "./Video";
import tw from "./twister.json";

export const TW_TOTAL = b(22);
const SAFE: React.CSSProperties = { position: "absolute", left: 70, right: 160, top: 250, bottom: 520 };
const CLIP_AT = b(4);

const Cap: React.FC<{ children: React.ReactNode; show: number; size?: number; color?: string }> = ({ children, show, size = 64, color = C.ink }) => (
  <div style={{ display: "inline-block", fontFamily: grot, fontSize: size, lineHeight: 1.1, color, background: "#0c0a08e0", borderRadius: 18,
    padding: "14px 26px", opacity: show, transform: `scale(${0.85 + 0.15 * show})`, transformOrigin: "left center" }}>{children}</div>
);

/* the demo's real output, word by word: right words get a green underline, the extra "zi" glows */
const Result: React.FC<{ f: number; from: number }> = ({ f, from }) => {
  const words = tw.demo_wrote.split(" "), said = tw.said.split(" ");
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 30px", fontFamily: serif, fontSize: 132, lineHeight: 1.05 }}>
      {words.map((w, k) => { const at = from + k * 9; if (f < at) return null; const p = pop(f, at, 11);
        const exact = w === said[k], extra = !exact && w.startsWith(said[k]) ? w.slice(said[k].length) : "";
        const judged = f > from + 40;
        return <span key={k} style={{ display: "inline-block", transform: `scale(${1.15 - 0.15 * p})`, color: C.ink,
          borderBottom: `8px solid ${judged && exact ? C.ok : "transparent"}`, paddingBottom: 4 }}>
          {extra ? <>{said[k]}<span style={{ color: judged ? C.glow : C.ink, textDecoration: judged ? `line-through ${C.err}` : "none",
            textDecorationThickness: 8 }}>{extra}</span></> : w}</span>; })}
    </div>
  );
};

export const Twister: React.FC<{ music: boolean }> = ({ music }) => {
  const f = useCurrentFrame();
  const s0 = CLIP_AT + tw.speech_start * FPS, s1 = CLIP_AT + tw.speech_end * FPS;
  const heard = (f - CLIP_AT) / FPS / tw.seconds;
  const k = Math.floor(((f - CLIP_AT) / FPS) * 50);
  const level = (i: number) => (f > CLIP_AT && f < CLIP_AT + tw.seconds * FPS ? (tw.bars[Math.min(tw.bars.length - 1, Math.max(0, k + (i % 7)))] || 0) ** 0.6
    : 0.07 + 0.06 * Math.exp(-((f % 18) / 4)));
  const phase = f < b(10) ? "listen" : f < b(17) ? "result" : "turn";
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Backdrop heat={phase === "listen" ? 0.5 : 1} />
      {music && <Audio src={staticFile("music_twister.wav")} volume={(fr) => (fr >= CLIP_AT && fr < CLIP_AT + tw.seconds * FPS ? 0.25 : 0.9)} />}
      <Sequence from={CLIP_AT} layout="none"><Audio src={staticFile("twister.wav")} volume={1} /></Sequence>
      {tw.demo_wrote.split(" ").map((_, i) => <Sfx key={i} at={b(10) + i * 9} v={0.35} />)}

      {phase === "listen" && (
        <div style={{ ...SAFE, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 30 }}>
          <Cap show={pop(f, 0, 200)} size={68}>Can AI keep up with an isiXhosa tongue twister? 😤</Cap>
          <Center style={{ top: 300 }}>
            <Orb size={720} level={level} />
            <div style={{ fontFamily: mono, fontSize: 34, letterSpacing: "0.16em", color: f > s0 && f < s1 + 6 ? C.glow : C.faint, marginTop: 6 }}>
              {f < CLIP_AT ? "TAP · SPEAK" : f < s1 + 6 ? "LISTENING…" : "WRITING…"}</div>
            <div style={{ width: 560, height: 10, borderRadius: 99, background: C.line, marginTop: 26, opacity: f >= CLIP_AT ? 1 : 0 }}>
              <div style={{ width: `${Math.max(0, Math.min(1, heard)) * 100}%`, height: "100%", borderRadius: 99, background: C.ember }} /></div>
          </Center>
        </div>
      )}

      {phase === "result" && (
        <div style={{ ...SAFE, display: "flex", flexDirection: "column", gap: 34 }}>
          <AbsoluteFill style={{ background: "#fff3e0", opacity: interpolate(f, [b(10), b(10) + 8], [0.7, 0], clamp), mixBlendMode: "screen", inset: -400 }} />
          <Cap show={pop(f, b(10), 200)} size={56} color={C.glow}>Thetha wrote:</Cap>
          <Result f={f} from={b(10) + 4} />
          <div style={{ marginTop: 30, opacity: pop(f, b(12), 200) }}>
            <div style={{ fontFamily: mono, fontSize: 30, letterSpacing: "0.14em", color: C.soft }}>I SAID:</div>
            <div style={{ fontFamily: serif, fontSize: 96, color: C.soft, marginTop: 6 }}>{tw.said}</div>
          </div>
          <div style={{ marginTop: "auto" }}><Cap show={pop(f, b(13), 12)} size={70}>so close 😅 just one extra "zi"</Cap></div>
        </div>
      )}

      {phase === "turn" && (
        <div style={{ ...SAFE, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 28, textAlign: "center" }}>
          <div style={{ fontFamily: grot, fontSize: 170, lineHeight: 1, color: C.ink, transform: `scale(${1.25 - 0.25 * pop(f, b(17), 10)})` }}>Your turn 👇</div>
          <div style={{ fontFamily: grot, fontSize: 58, lineHeight: 1.15, color: C.ink, opacity: pop(f, b(18), 200) }}>
            say it in isiXhosa,<br /><span style={{ color: C.glow }}>see if it keeps up</span></div>
          <div style={{ marginTop: 30, opacity: pop(f, b(19), 200) }}>
            <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: 110, color: C.ink, lineHeight: 1 }}>
              Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
            <div style={{ fontFamily: mono, fontSize: 30, letterSpacing: "0.14em", color: C.glow, marginTop: 12 }}>FREE · LINK IN BIO</div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
