// R-0027 teaser (~29 s, vertical): the founder's own recording, transcribed live by the old and the new browser demo
// side by side, then what changed, one number, the link. Every word on screen is real (prepare_teaser.py -> teaser.json).
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Backdrop, C, Center, FPS, Mono, Orb, Sfx, b, clamp, grot, mono, pop, scramble, serif } from "./Video";
import t from "./teaser.json";

export const TZ_TOTAL = b(48);
const VOICE_AT = b(3), VOICE_END = VOICE_AT + Math.round(t.seconds * FPS);
const SAFE: React.CSSProperties = { position: "absolute", left: 80, right: 80, top: 210, bottom: 300 };
type W = { w: string; ok: boolean; t: number };

/* 0-3 beats: the hook */
const Hook: React.FC = () => {
  const f = useCurrentFrame(), p = pop(f, 2, 11), out = interpolate(f, [b(2.6), b(3)], [1, 0], clamp);
  return (
    <Center style={{ opacity: out, padding: "0 90px" }}>
      <div style={{ fontFamily: grot, fontSize: 150, lineHeight: 0.98, color: C.ink, textAlign: "center",
        transform: `scale(${1.25 - 0.25 * p})`, filter: `blur(${(1 - p) * 10}px)` }}>
        Thetha got<br /><span style={{ color: C.glow }}>an upgrade.</span></div>
      <Mono u={1} style={{ marginTop: 50, opacity: pop(f, b(1.2), 200) }}>same voice · old demo vs new</Mono>
    </Center>
  );
};

/* one demo's transcript, word by word as the voice says them */
const Panel: React.FC<{ label: string; words: W[]; errors: number; of: number; isNew: boolean; f: number; start: number }> =
  ({ label, words, errors, of, isNew, f, start }) => {
    const end = start + Math.round(t.seconds * FPS), done = f > end + 6, tally = pop(f, end + 8, 12);
    return (
      <div style={{ borderRadius: 34, padding: "34px 40px 30px", background: isNew ? "#14211acc" : "#1a1410cc",
        border: `2px solid ${isNew ? "#6fd0a655" : "#ff6b5733"}`, minHeight: 470 }}>
        <div style={{ fontFamily: mono, fontSize: 26, letterSpacing: "0.16em", color: isNew ? C.ok : C.soft }}>{label}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "2px 20px", fontFamily: serif, fontSize: 68, lineHeight: 1.12, marginTop: 18 }}>
          {words.map((w, k) => {
            const at = start + Math.round(w.t * FPS), shown = f >= at - 7, res = f >= at, p = pop(f, at, 12);
            if (!shown) return null;
            const bad = res && !w.ok, jitter = bad ? Math.sin((f - at) * 2.2) * Math.max(0, 10 - (f - at)) : 0;
            return <span key={k} style={{ display: "inline-block", color: !res ? "#e2732b88" : bad ? C.err : C.ink,
              transform: `translateX(${jitter}px) scale(${res ? 1.1 - 0.1 * p : 1})`,
              textDecoration: bad && !isNew ? "underline wavy #ff6b5799" : "none", textUnderlineOffset: 10,
              textShadow: res && w.ok && isNew ? `0 0 ${30 * (1 - p)}px ${C.ok}` : "none" }}>{res ? w.w : scramble(w.w, f, k)}</span>;
          })}
        </div>
        <div style={{ marginTop: 22, opacity: done ? 1 : 0, transform: `scale(${0.85 + 0.15 * tally})`, transformOrigin: "left center",
          fontFamily: grot, fontSize: 52, color: isNew ? C.ok : C.err }}>
          {errors} of {of} words wrong{isNew ? <div style={{ fontFamily: serif, fontSize: 44, color: C.soft, marginTop: 6 }}>"theatre" 😅 still learning</div> : null}</div>
      </div>
    );
  };

/* 3-28 beats: the voice plays once; both demos write it at the same time */
const Duel: React.FC = () => {
  const f = useCurrentFrame(), start = 0;  // this Sequence starts with the voice
  const lv = t.level[Math.max(0, Math.min(t.level.length - 1, f))] ?? 0;
  const level = (i: number) => (f < 0 || f > t.level.length ? 0.06 : 0.05 + lv * (0.55 + 0.45 * Math.sin(i * 1.3 + f / 3)));
  return (
    <AbsoluteFill>
      <Audio src={staticFile("teaser_voice.wav")} />
      {t.outputs.new.words.map((w, k) => (w.ok ? <Sfx key={k} at={Math.round(w.t * FPS)} v={0.16} /> : null))}
      <div style={{ ...SAFE, display: "flex", flexDirection: "column", justifyContent: "center", gap: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 26, opacity: pop(f, 0, 200) }}>
          <Orb size={190} level={level} />
          <div>
            <div style={{ fontFamily: grot, fontSize: 58, color: C.ink, lineHeight: 1 }}>my voice</div>
            <Mono u={1} size={24} style={{ marginTop: 10 }}>one recording · two demos</Mono>
          </div>
        </div>
        <Panel label={`OLD DEMO · ${t.outputs.old.run}`} words={t.outputs.old.words} errors={t.outputs.old.errors} of={t.outputs.old.of} isNew={false} f={f} start={start} />
        <Panel label={`NEW DEMO · ${t.outputs.new.run}`} words={t.outputs.new.words} errors={t.outputs.new.errors} of={t.outputs.new.of} isNew f={f} start={start} />
      </div>
    </AbsoluteFill>
  );
};

/* 28-34 beats: what changed. A long recording is cut into pieces at its pauses. */
const Changed: React.FC = () => {
  const f = useCurrentFrame(), N = 64;
  const bars = Array.from({ length: N }, (_, i) => t.level[Math.floor((i / N) * t.level.length)] ?? 0);
  const cuts = [13, 27, 41, 52];  // gaps between bars where the pieces separate
  const split = interpolate(f, [b(1.6), b(2.6)], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const out = interpolate(f, [b(5.6), b(6)], [1, 0], clamp);
  return (
    <Center style={{ opacity: out, gap: 70 }}>
      {cuts.map((c, k) => <Sfx key={k} at={b(1.2) + k * 4} v={0.3} />)}
      <div style={{ display: "flex", alignItems: "center", height: 300 }}>
        {bars.map((v, i) => {
          const piece = cuts.filter(c => i >= c).length;
          const grow = interpolate(f, [i * 0.4, i * 0.4 + 8], [0, 1], clamp);
          return <div key={i} style={{ width: 8, marginRight: 4, height: 14 + v * 260 * grow, borderRadius: 6,
            background: piece % 2 ? C.glow : C.ember, transform: `translateX(${piece * 34 * split}px)` }} />;
        })}
      </div>
      <div style={{ textAlign: "center", padding: "0 80px" }}>
        <div style={{ fontFamily: grot, fontSize: 120, lineHeight: 1, color: C.ink, opacity: pop(f, b(0.4), 200),
          transform: `translateY(${(1 - pop(f, b(0.4), 12)) * 60}px)` }}>+245 hours</div>
        <div style={{ fontFamily: serif, fontSize: 70, color: C.glow, marginTop: 16, opacity: pop(f, b(1), 200) }}>of real isiXhosa speech</div>
        <Mono u={1} size={26} style={{ marginTop: 40, opacity: pop(f, b(2.6), 200) }}>long conversations, cut at the pauses</Mono>
      </div>
    </Center>
  );
};

/* 34-40 beats: the number */
const Number_: React.FC = () => {
  const f = useCurrentFrame(), n = t.numbers;
  const v = interpolate(f, [b(0.6), b(2.4)], [n.before, n.now], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const out = interpolate(f, [b(5.6), b(6)], [1, 0], clamp), W = 820;
  return (
    <Center style={{ opacity: out, gap: 40, padding: "0 130px" }}>
      <Mono u={1} size={28} style={{ textAlign: "center", lineHeight: 1.6 }}>letters wrong in every 100<br />people speaking freely</Mono>
      <div style={{ fontFamily: grot, fontSize: 300, lineHeight: 1, color: f > b(2.4) ? C.ok : C.ink }}>{v.toFixed(1)}</div>
      <div style={{ width: W, height: 34, borderRadius: 17, background: C.line, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: (W * v) / n.before, borderRadius: 17,
          background: f > b(2.4) ? C.ok : C.err }} />
      </div>
      <div style={{ fontFamily: serif, fontSize: 52, color: C.soft, opacity: pop(f, b(2.6), 200) }}>
        was <span style={{ color: C.err }}>{n.before}</span> · now <span style={{ color: C.ok }}>{n.now}</span></div>
    </Center>
  );
};

/* 40-48 beats: try it */
const Outro: React.FC = () => {
  const f = useCurrentFrame(), burst = interpolate(f, [0, 22], [0, 1], clamp);
  return (
    <Center style={{ gap: 34, padding: "0 90px", opacity: interpolate(f, [b(7.2), b(8)], [1, 0], clamp) }}>
      <div style={{ transform: `scale(${0.7 + 0.3 * pop(f, 0, 14)})` }}><Orb size={460} burst={burst} /></div>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: 150, lineHeight: 1, color: C.ink, opacity: pop(f, 6, 200) }}>
        Thetha<span style={{ color: C.ember, fontStyle: "normal" }}>.</span></div>
      <div style={{ fontFamily: grot, fontSize: 58, color: C.ink, textAlign: "center", lineHeight: 1.15, opacity: pop(f, b(1), 200) }}>
        speak isiXhosa,<br />see it written</div>
      <Mono u={1} size={27} color={C.glow} style={{ textAlign: "center", lineHeight: 1.7, opacity: pop(f, b(2), 200) }}>
        free · runs in your browser<br />nothing you say is uploaded<br />link in the post</Mono>
      <div style={{ fontFamily: mono, fontSize: 25, color: C.soft, textAlign: "center", lineHeight: 1.6, marginTop: 30, opacity: pop(f, b(3), 200) }}>
        new data: Swivuriso · African Next Voices (DSFSI, University of Pretoria)</div>
    </Center>
  );
};

const PARTS: [number, number, React.FC][] = [[0, 3, Hook], [3, 28, Duel], [28, 34, Changed], [34, 40, Number_], [40, 48, Outro]];

export const Teaser: React.FC<{ music: boolean }> = ({ music }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Backdrop heat={f < b(3) ? 0.5 : f < b(28) ? 0.7 : 1} />
      {music && <Audio src={staticFile("music_teaser.wav")} volume={(fr) => (fr >= VOICE_AT && fr < VOICE_END ? 0.28 : 0.9)} />}
      {PARTS.map(([s, e, P], i) => <Sequence key={i} from={b(s)} durationInFrames={b(e - s)}><P /></Sequence>)}
    </AbsoluteFill>
  );
};
