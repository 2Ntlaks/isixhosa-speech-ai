"""Read Google FLEURS split files (xh_za train.tsv / dev.tsv / test.tsv) into the same clip format as nchlt.load_split.

TSV columns: sentence id, wav file name, raw transcript, normalised transcript, characters, number of samples, gender.
We use the normalised transcript (lowercase, no punctuation), the same style as NCHLT. Audio is 16 kHz, so
duration = samples / 16000. FLEURS has no speaker ids; every clip gets speaker "fleurs".
"""
import csv
import os

csv.field_size_limit(10 ** 8)


def load_split(tsv_path, audio_dir):
    clips = []
    with open(tsv_path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            sentence_id, wav, _raw, norm, *_rest, samples, gender = row
            clips.append({
                "id": "fleurs_" + os.path.splitext(wav)[0],
                "speaker": "fleurs",
                "gender": gender.strip().lower(),
                "path": os.path.join(audio_dir, wav),
                "duration": int(samples) / 16000,
                "text": norm.strip(),
                "sentence_id": sentence_id,
            })
    return clips
