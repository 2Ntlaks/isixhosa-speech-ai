"""Talk to the model: a small speech-to-text API and recording page on this laptop (D-0014).

  .venv/Scripts/python src/live.py [--model data/models/R-0012] [--port 7860]
Then open http://127.0.0.1:7860 and press record. Runs on the CPU; listens on this computer only (127.0.0.1).

API (what the page uses; any program can call it the same way):
  POST /transcribe?model=R-0012&keep=1   body: audio in any format ffmpeg reads (webm, ogg, m4a, wav)
       -> {"id", "text", "model", "audio_seconds", "compute_seconds"}
  POST /correct   {"id": ..., "said": "what was really said"}   -> {"ok": true}
  GET  /models    -> the models available in data/models/
With keep=1 the recording is saved to data/my_voice/live/<id>.wav and every result and correction is appended to
data/my_voice/live/log.jsonl (gitignored). Corrections are the founder's own transcripts: stage 4 material.
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
PAGE = os.path.join(ROOT, "src", "live.html")
SR, CHUNK = 16000, 30 * 16000  # Whisper hears at most 30 s at a time, so longer recordings go in 30 s pieces

FFMPEG = shutil.which("ffmpeg")
loaded, lock = {}, threading.Lock()


def available():
    """Models whose weights are fully downloaded (the aws CLI only creates model.safetensors when a download completes)."""
    return sorted(d for d in os.listdir(MODELS) if os.path.isfile(os.path.join(MODELS, d, "model.safetensors")))


def model(name):
    if name not in loaded:
        path = os.path.join(MODELS, name)
        t = time.time()
        loaded[name] = (WhisperProcessor.from_pretrained(path),
                        WhisperForConditionalGeneration.from_pretrained(path, torch_dtype=torch.float32).eval())
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
    proc, m = model(name)
    pieces = [audio[i:i + CHUNK] for i in range(0, len(audio), CHUNK)]
    feats = proc(pieces, sampling_rate=SR, return_tensors="pt").input_features
    with lock, torch.no_grad():  # one recording at a time; the CPU is the bottleneck anyway
        out = m.generate(feats, language="sw", task="transcribe", max_new_tokens=225)  # sw tag, as trained (D-0007)
    return " ".join(t.strip() for t in proc.batch_decode(out, skip_special_tokens=True)).strip()


def log(entry):
    os.makedirs(KEEP, exist_ok=True)
    with open(os.path.join(KEEP, "log.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
        if path == "/models":
            return self.send(200, available())
        self.send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            if url.path == "/transcribe":
                q = parse_qs(url.query)
                name = q.get("model", [default])[0]
                if name not in available():
                    return self.send(400, {"error": f"model {name} is not (fully) downloaded"})
                audio = decode(body)
                if len(audio) < SR * 0.3:
                    return self.send(400, {"error": "recording too short"})
                t = time.time()
                text = transcribe(audio, name)
                rid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                res = {"id": rid, "text": text, "model": name, "audio_seconds": round(len(audio) / SR, 2),
                       "compute_seconds": round(time.time() - t, 2)}
                if q.get("keep", ["0"])[0] == "1":
                    os.makedirs(KEEP, exist_ok=True)
                    sf.write(os.path.join(KEEP, rid + ".wav"), audio, SR, subtype="PCM_16")
                    log({**res, "file": rid + ".wav"})
                print(f"{name} {res['audio_seconds']} s audio -> {res['compute_seconds']} s: {text}", flush=True)
                return self.send(200, res)
            if url.path == "/correct":
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
    ap.add_argument("--model", default="R-0012", help="folder name in data/models/")
    ap.add_argument("--port", type=int, default=7860)
    a = ap.parse_args()
    if not FFMPEG:
        sys.exit("ffmpeg not found on PATH (needed to read browser recordings)")
    default = a.model
    model(default)
    transcribe(np.zeros(SR, dtype=np.float32), default)  # warm-up, so the first real recording isn't slow
    print(f"ready: open http://127.0.0.1:{a.port}  (model {default}, CPU, {torch.get_num_threads()} threads)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
