"""Synthesise the film's soundtrack (no samples, no licences): a 100 BPM score laid out on the same beat grid as
src/Video.tsx (1 beat = 0.6 s = 18 frames), plus short effects the film places itself.

  ../../.venv/Scripts/python sound.py
Writes public/music.wav (the whole score, 72 beats) and public/tick.wav, public/glitch.wav.
"""
import os

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR, BEAT, BEATS = 44100, 0.6, 72
rng = np.random.default_rng(11)
out = np.zeros(int(SR * BEAT * BEATS) + SR)


def at(beat):
    return int(round(beat * BEAT * SR))


def add(sig, beat, gain=1.0):
    i = at(beat)
    out[i:i + len(sig)] += sig[: max(0, len(out) - i)] * gain


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def kick(f0=150, f1=45, dec=0.35, sec=0.5):
    t = tt(sec)
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)


def hat(sec=0.06):
    t = tt(sec)
    return np.diff(rng.standard_normal(t.size + 1)) * np.exp(-t * 70) * 0.25


def tongue_click():
    """A dry, resonant transient: the closest a synth gets to an isiXhosa click."""
    t = tt(0.12)
    ring = np.sin(2 * np.pi * 1850 * t) * np.exp(-t * 90)
    pop = np.sin(2 * np.pi * 420 * t) * np.exp(-t * 260)
    burst = np.diff(rng.standard_normal(t.size + 1)) * np.exp(-t * 600)
    return (ring * 0.7 + pop * 0.6 + burst * 0.5)


def tone(freqs, sec, amp=1.0, attack=0.3, release=1.0):
    t = tt(sec)
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t + 1) for f in freqs)
    env = np.minimum(1, t / attack) * np.minimum(1, (t[-1] - t) / release)
    return s * env * amp


# A · cold open: three clicks (c, q, x) on beats 1-3, then a sub swell
for b in (1, 2, 3):
    add(tongue_click(), b, 0.9)
add(tone([55], BEAT * 7, 0.18, attack=2.5, release=1.5), 3)

# B · the language reel: a soft heartbeat
for b in range(4, 10):
    add(kick(110, 40, 0.25), b, 0.45)

# C · the loop: tension drone and an uneasy heartbeat every 2 beats
add(tone([55, 58.3], BEAT * 7, 0.12, attack=1, release=0.4), 10)
for b in range(10, 17, 2):
    add(kick(120, 38, 0.3), b, 0.5)

# D · "So I taught it.": a thump per word, on the same half-beats as the words
for b in (17, 17.5, 18, 18.5):
    add(kick(90, 35, 0.45, 0.8), b, 0.8)

# E · INTRODUCING: four-beat riser (brightening noise + rising tone)
t = tt(BEAT * 4)
p = t / t[-1]
noise = rng.standard_normal(t.size)
bright = np.diff(noise, prepend=0) * p + np.convolve(noise, np.ones(30) / 30, "same") * (1 - p)
sweep = np.sin(2 * np.pi * np.cumsum(180 + 900 * p ** 2) / SR)
add((bright * 0.35 + sweep * 0.25) * p ** 2.2, 20)

# F · the reveal: impact on beat 24
t = tt(2.5)
impact = kick(95, 30, 0.9, 2.5) + np.diff(rng.standard_normal(t.size + 1)) * np.exp(-t * 4) * 0.25
add(impact, 24, 1.0)

# G-K · the groove from beat 24 to the end: kick, offbeat hats, bass line, warm pad (Am F C G)
roots = [55.0, 43.65, 65.41, 49.0]
chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [196, 261.6, 329.6], [196, 246.9, 293.7]]
for b in range(25, 70):
    add(kick(), b, 0.75)
    add(hat(), b + 0.5, 0.6)
    if b % 2 == 0:
        add(hat(0.03), b + 0.25, 0.3)
for bar, b in enumerate(range(24, 70, 4)):
    r, ch = roots[bar % 4], chords[bar % 4]
    bt = tt(BEAT * 4)
    bass = (np.sin(2 * np.pi * r * bt) + 0.4 * np.sin(2 * np.pi * 2 * r * bt)) * np.minimum(1, bt / 0.02) * np.exp(-bt / 1.6)
    add(bass, b, 0.35)
    add(tone(ch, BEAT * 4, 0.035, attack=0.6, release=0.8), b)
add(impact * 0.6, 63)  # the end card lands on a hit

# master: gentle limiter and fade-out over the last 4 beats
fade = np.ones_like(out)
i0, i1 = at(BEATS - 4), at(BEATS)
fade[i0:i1] = np.linspace(1, 0, i1 - i0)
fade[i1:] = 0
out = np.tanh(out * fade * 1.1) * 0.85
sf.write(os.path.join(HERE, "public", "music.wav"), out.astype("float32"), SR, subtype="PCM_16")

# effects the film places itself
t = tt(0.02)
sf.write(os.path.join(HERE, "public", "tick.wav"), (np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 300) * 0.4).astype("float32"), SR, subtype="PCM_16")
t = tt(0.25)
g = np.round(rng.standard_normal(t.size) * 3) / 3 * (np.sin(2 * np.pi * 37 * t) > 0) * np.exp(-t * 6) * 0.3
sf.write(os.path.join(HERE, "public", "glitch.wav"), g.astype("float32"), SR, subtype="PCM_16")
print(f"music.wav {len(out) / SR:.1f} s, peak {np.abs(out).max():.2f}")

# ---- TikTok cut (src/TikTok.tsx): 32 beats, energy from frame 0, impact on beat 8, groove to the end ----
out = np.zeros(int(SR * BEAT * 32) + SR)
for b_ in range(0, 8):
    add(kick(120, 40, 0.3), b_, 0.55)                 # tense pulse under the loop
    add(hat(0.03), b_ + 0.5, 0.35)
add(tone([55, 58.3], BEAT * 8, 0.12, attack=0.2, release=0.3), 0)
add(impact, 8, 1.0)                                    # "so I trained my own."
for b_ in range(10, 32):
    add(kick(), b_, 0.75)
    add(hat(), b_ + 0.5, 0.6)
for bar, b_ in enumerate(range(10, 32, 4)):
    r, ch = roots[bar % 4], chords[bar % 4]
    bt = tt(BEAT * 4)
    add((np.sin(2 * np.pi * r * bt) + 0.4 * np.sin(2 * np.pi * 2 * r * bt)) * np.minimum(1, bt / 0.02) * np.exp(-bt / 1.6), b_, 0.35)
    add(tone(ch, BEAT * 4, 0.035, attack=0.4, release=0.6), b_)
for b_ in (20, 21.5, 23):
    add(kick(90, 35, 0.45, 0.8), b_, 0.7)              # the three stat punches
out = np.tanh(out * 1.1) * 0.85
sf.write(os.path.join(HERE, "public", "music_tiktok.wav"), out.astype("float32"), SR, subtype="PCM_16")
print(f"music_tiktok.wav {len(out) / SR:.1f} s")

# ---- Tongue-twister TikTok (src/Twister.tsx): 22 beats ----
out = np.zeros(int(SR * BEAT * 22) + SR)
for b_ in range(0, 4):
    add(kick(120, 40, 0.3), b_, 0.6)
    add(hat(0.03), b_ + 0.5, 0.35)
for b_ in (1, 2, 3):
    add(tongue_click(), b_ + 0.75, 0.5)
for b_ in range(4, 10, 2):
    add(kick(100, 38, 0.3), b_, 0.3)                  # quiet heartbeat under the voice
add(impact, 10, 0.8)                                   # the result appears
for b_ in range(13, 22):
    add(kick(), b_, 0.75)
    add(hat(), b_ + 0.5, 0.6)
for bar, b_ in enumerate(range(13, 22, 4)):
    bt = tt(BEAT * 4)
    add((np.sin(2 * np.pi * roots[bar % 4] * bt) + 0.4 * np.sin(4 * np.pi * roots[bar % 4] * bt)) * np.minimum(1, bt / 0.02) * np.exp(-bt / 1.6), b_, 0.35)
    add(tone(chords[bar % 4], BEAT * 4, 0.035, attack=0.4, release=0.6), b_)
add(impact * 0.5, 17)
out = np.tanh(out * 1.1) * 0.85
sf.write(os.path.join(HERE, "public", "music_twister.wav"), out.astype("float32"), SR, subtype="PCM_16")
print(f"music_twister.wav {len(out) / SR:.1f} s")

# ---- R-0027 teaser (src/Teaser.tsx): 48 beats. Hook 0-3, the founder's voice 3-28 (score stays low), riser into
# "what changed" at 28, groove to the end, hits on the number (34, 35.5) and the end card (40), fade over the last 3 ----
out = np.zeros(int(SR * BEAT * 48) + SR)
add(tongue_click(), 0, 0.9)
add(tone([55], BEAT * 4, 0.16, attack=1.2, release=1.0), 0)
add(tone([110, 164.8], BEAT * 25, 0.025, attack=2.0, release=2.0), 3)  # a warm bed under the voice
for b_ in range(4, 28, 2):
    add(kick(110, 40, 0.25), b_, 0.35)
t = tt(BEAT * 2)
p = t / t[-1]
add((np.diff(rng.standard_normal(t.size), prepend=0) * p * 0.3 + np.sin(2 * np.pi * np.cumsum(200 + 900 * p ** 2) / SR) * 0.25) * p ** 2, 26)
t = tt(2.5)
add(kick(95, 30, 0.9, 2.5) + np.diff(rng.standard_normal(t.size + 1)) * np.exp(-t * 4) * 0.25, 28, 1.0)
for b_ in range(29, 46):
    add(kick(), b_, 0.75)
    add(hat(), b_ + 0.5, 0.6)
for bar, b_ in enumerate(range(28, 48, 4)):
    r, ch = roots[bar % 4], chords[bar % 4]
    bt = tt(BEAT * 4)
    add((np.sin(2 * np.pi * r * bt) + 0.4 * np.sin(2 * np.pi * 2 * r * bt)) * np.minimum(1, bt / 0.02) * np.exp(-bt / 1.6), b_, 0.35)
    add(tone(ch, BEAT * 4, 0.035, attack=0.4, release=0.6), b_)
for b_ in (34, 35.5):
    add(kick(90, 35, 0.45, 0.8), b_, 0.7)
add(impact * 0.6, 40)
fade = np.ones_like(out)
i0, i1 = at(45), at(48)
fade[i0:i1] = np.linspace(1, 0, i1 - i0)
fade[i1:] = 0
out = np.tanh(out * fade * 1.1) * 0.85
sf.write(os.path.join(HERE, "public", "music_teaser.wav"), out.astype("float32"), SR, subtype="PCM_16")
print(f"music_teaser.wav {len(out) / SR:.1f} s")
