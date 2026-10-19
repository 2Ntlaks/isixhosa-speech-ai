"""Read the Soapies English-isiXhosa code-switched corpus (balanced_engxho.xml + official dev/test utterance id lists)
into the same clip format as nchlt.load_split. Research-only data: test/dev use only, never training (D-0016).

Transcript conventions in the corpus, and what we do with them:
- "!" stands for an apostrophe (i!m = I'm, ucing!ukuba): turned into "'", which scoring.normalise keeps.
- "_" marks a word broken at a language switch (i_ grapefruit = i-grapefruit, u_ join _e = ujoine): left as is;
  scoring.normalise turns "_" into a space, the same split form as FLEURS hyphens get (D-0010).
- Durations in the XML are in milliseconds. Audio is 32 kHz mono; evaluators resample to 16 kHz.
"""
import os
import xml.etree.ElementTree as ET


def load_ids(path):
    with open(path, encoding="utf-8") as f:
        return set(f.read().split())


def load_split(xml_path, ids_path, audio_dir):
    """One dict per utterance in the id list: id, speaker, path, duration (s), text, langs, segments [(lang, text)]."""
    wanted = load_ids(ids_path)
    wavs = {os.path.splitext(f)[0]: os.path.join(d, f)
            for d, _, files in os.walk(audio_dir) for f in files if f.endswith(".wav")}
    clips = []
    for utt in ET.parse(xml_path).getroot().iter("utterance"):
        uid = os.path.splitext(utt.findtext("audio"))[0]
        if uid not in wanted:
            continue
        segs = [(s.findtext("lang_id"), (s.findtext("transcription") or "").replace("!", "'").strip())
                for s in utt.iter("utterance_segment")]
        clips.append({
            "id": uid,
            "speaker": utt.findtext("speaker_id"),
            "path": wavs.get(uid),
            "duration": float(utt.findtext("duration")) / 1000,
            "text": " ".join(t for _, t in segs),
            "langs": "+".join(sorted({lang for lang, _ in segs})),
            "segments": segs,
        })
    return clips
