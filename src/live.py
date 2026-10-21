"""Thetha: talk to the model. A small speech-to-text API and recording page on this laptop (D-0014).

  CT2_USE_MKL=0 .venv/Scripts/python src/live.py [--models R-0019-int8,R-0007-int8] [--port 7860]
Then open http://127.0.0.1:7860. Runs on the CPU; listens on this computer only (127.0.0.1).
Models are folders in data/models/: a transformers checkpoint (model.safetensors, loaded in --dtype) or a CTranslate2
copy (model.bin, int8: ct2-transformers-converter --quantization int8; same answers, faster, R-0013). The first model
in --models is the default; all of them stay loaded (8-bit medium ~0.8 GB, small ~0.25 GB).

API (what the page uses; any program can call it the same way):
  POST /transcribe?model=R-0019-int8&also=R-0007-int8&keep=1
       body: audio in any format ffmpeg reads (browser webm, WhatsApp ogg/opus, m4a, mp3, wav), up to 100 MB
       -> {"id", "text", "model", "audio_seconds", "compute_seconds", "also": {"model", "text", "compute_seconds"}}
  POST /correct   {"id": ..., "said": "what was really said"}   -> {"ok": true}
  GET  /models    -> the models this server offers, default first
  GET  /corrections.tsv -> every saved correction: id, model output, what was really said
With keep=1 the recording is saved to data/my_voice/live/<id>.wav and every result and correction is appended to
data/my_voice/live/log.jsonl (gitignored). Corrections are the founder's own transcripts: stage 4 material.

--public (the online demo, D-0019): listens on all addresses, never stores audio or text (keep is ignored, /correct and
/corrections.tsv are off), and GET /config tells the page to hide keep, save and download.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np
import soundfile as sf
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "data", "models")
KEEP = os.path.join(ROOT, "data", "my_voice", "live")
LOG = os.path.join(KEEP, "log.jsonl")
PAGE = os.path.join(ROOT, "src", "live.html")
SR, CHUNK = 16000, 30 * 16000  # Whisper hears at most 30 s at a time, so longer recordings go in 30 s pieces
MAX_BYTES = 100 * 1024 * 1024

FFMPEG = shutil.which("ffmpeg")
loaded, lock = {}, threading.Lock()
offered = []  # set in main: the models this server serves, default first
PUBLIC = False  # set in main (--public)


def complete(name):
    """True when the model's weights are complete (the aws CLI only creates model.safetensors when a download ends)."""
    return any(os.path.isfile(os.path.join(MODELS, name, f)) for f in ("model.safetensors", "model.bin"))


def model(name):
    if name not in loaded:
        path = os.path.join(MODELS, name)
        t = time.time()
        proc = WhisperProcessor.from_pretrained(path)
        if os.path.isfile(os.path.join(path, "model.bin")):  # CTranslate2, 8-bit weights
            import ctranslate2
            m = ctranslate2.models.Whisper(path, device="cpu", compute_type="int8", intra_threads=torch.get_num_threads())
        else:
            m = WhisperForConditionalGeneration.from_pretrained(path, torch_dtype=dtype, low_cpu_mem_usage=True).eval()
        loaded[name] = (proc, m)
        print(f"loaded {name} in {time.time() - t:.0f} s", flush=True)
    return loaded[name]


def decode(data):
    """Any audio file -> 16 kHz mono float32, via ffmpeg."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "pipe:1"], input=data, capture_output=True)
    if r.returncode:
        raise ValueError("could not read the audio: " + r.stderr.decode(errors="replace")[-300:])
    return np.frombuffer(r.stdout, dtype=np.float32)


def transcribe(audio, name):
    """-> (text, seconds). Same prompt (<|sw|>, transcribe, no timestamps) as the test evaluations; int8 models use beam 5 (R-0021)."""
    proc, m = model(name)
    pieces = [audio[i:i + CHUNK] for i in range(0, len(audio), CHUNK)]
    feats = proc(pieces, sampling_rate=SR, return_tensors="pt").input_features
    with lock, torch.no_grad():  # one recording at a time; the CPU is the bottleneck anyway
        t = time.time()
        if isinstance(m, WhisperForConditionalGeneration):
            out = m.generate(feats.to(dtype), language="sw", task="transcribe", max_new_tokens=225)  # sw tag (D-0007)
        else:
            import ctranslate2
            prompt = proc.tokenizer.convert_tokens_to_ids(["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
            res = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats.numpy())), [prompt] * len(pieces),
                             beam_size=5, max_length=225)  # R-0021: CER 5.01 -> 4.73, no slowdown
            out = [r.sequences_ids[0] for r in res]
        secs = round(time.time() - t, 2)
    return " ".join(t.strip() for t in proc.batch_decode(out, skip_special_tokens=True)).strip(), secs


def log(entry):
    os.makedirs(KEEP, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def corrections():
    """Latest correction per recording, with what the model wrote: id, model, model output, what was really said."""
    if not os.path.isfile(LOG):
        return []
    results, said = {}, {}
    for line in open(LOG, encoding="utf-8"):
        e = json.loads(line)
        if "said" in e:
            said[e["id"]] = e["said"]
        elif "text" in e:
            results[e["id"]] = e
    return [(i, results.get(i, {}).get("model", ""), results.get(i, {}).get("text", ""), s) for i, s in sorted(said.items())]


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
        if path == "/models":
            return self.send(200, offered)
        if path == "/config":
            return self.send(200, {"public": PUBLIC})
        if path == "/corrections.tsv" and not PUBLIC:
            flat = lambda s: " ".join(str(s).split())  # tabs/newlines inside text would break the columns
            rows = ["id\tmodel\tmodel_wrote\treally_said"] + ["\t".join(flat(x) for x in r) for r in corrections()]
            return self.send(200, ("\n".join(rows) + "\n").encode(), "text/tab-separated-values; charset=utf-8",
                             {"Content-Disposition": 'attachment; filename="thetha-corrections.tsv"'})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        size = int(self.headers.get("Content-Length", 0))
        if size > MAX_BYTES:
            return self.send(413, {"error": "file too large (100 MB max)"})
        body = self.rfile.read(size)
        try:
            if url.path == "/transcribe":
                q = parse_qs(url.query)
                name, also = q.get("model", [offered[0]])[0], q.get("also", [""])[0]
                if name not in offered or (also and also not in offered):
                    return self.send(400, {"error": "unknown model"})
                audio = decode(body)
                if len(audio) < SR * 0.3:
                    return self.send(400, {"error": "too short"})
                text, secs = transcribe(audio, name)
                rid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                res = {"id": rid, "text": text, "model": name, "audio_seconds": round(len(audio) / SR, 2), "compute_seconds": secs}
                if also and also != name:
                    t2, s2 = transcribe(audio, also)
                    res["also"] = {"model": also, "text": t2, "compute_seconds": s2}
                if q.get("keep", ["0"])[0] == "1" and not PUBLIC:
                    os.makedirs(KEEP, exist_ok=True)
                    sf.write(os.path.join(KEEP, rid + ".wav"), audio, SR, subtype="PCM_16")
                    log({**res, "file": rid + ".wav"})
                print(f"{name} {res['audio_seconds']} s audio -> {secs} s: {text}"
                      + (f"  | {also}: {res['also']['text']}" if "also" in res else ""), flush=True)
                return self.send(200, res)
            if url.path == "/correct" and not PUBLIC:
                j = json.loads(body)
                log({"id": str(j["id"]), "said": str(j["said"]).strip(),
                     "corrected_at": datetime.datetime.now().isoformat(timespec="seconds")})
                return self.send(200, {"ok": True})
            self.send(404, {"error": "not found"})
        except Exception as e:  # report, keep serving
            print("error:", repr(e), flush=True)
            self.send(500, {"error": str(e)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="R-0019-int8,R-0007-int8",
                    help="comma-separated folder names in data/models/; the first is the default")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--models-dir", default=MODELS, help="folder holding the model folders (default data/models)")
    ap.add_argument("--public", action="store_true", help="online demo: all addresses, nothing stored")
    ap.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16",
                    help="for transformers checkpoints: bfloat16 halves memory (medium ~1.9 GB instead of ~3.5 GB)")
    a = ap.parse_args()
    if not FFMPEG:
        sys.exit("ffmpeg not found on PATH (needed to read browser recordings)")
    dtype = getattr(torch, a.dtype)
    MODELS, PUBLIC = a.models_dir, a.public
    offered[:] = [m for m in a.models.split(",") if complete(m)]
    if not offered:
        sys.exit(f"none of {a.models} is in {MODELS}")
    for m in offered:
        model(m)
        transcribe(np.zeros(SR, dtype=np.float32), m)  # warm-up, so the first real recording isn't slow
    host = "0.0.0.0" if PUBLIC else "127.0.0.1"
    print(f"ready: open http://127.0.0.1:{a.port}  (models {', '.join(offered)}; CPU, {torch.get_num_threads()} threads"
          + ("; public: nothing stored" if PUBLIC else "") + ")", flush=True)
    ThreadingHTTPServer((host, a.port), Handler).serve_forever()
