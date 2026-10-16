"""Read the NCHLT corpus transcription XML (nchlt_xho.trn.xml / nchlt_xho.tst.xml) into a list of clips."""
import os
import xml.etree.ElementTree as ET


def load_split(xml_path, root):
    """One dict per recording: id, speaker, gender, path (under root), duration (s), text (the orth line)."""
    clips = []
    for spk in ET.parse(xml_path).getroot().iter("speaker"):
        for rec in spk.iter("recording"):
            audio = rec.get("audio")
            clips.append({
                "id": os.path.splitext(os.path.basename(audio))[0],
                "speaker": spk.get("id"),
                "gender": spk.get("gender"),
                "path": os.path.join(root, audio),
                "duration": float(rec.get("duration")),
                "text": (rec.findtext("orth") or "").strip(),
            })
    return clips
