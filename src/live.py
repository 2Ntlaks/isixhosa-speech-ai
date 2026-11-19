"""Thetha: talk to the model. A small speech-to-text API and recording page on this laptop (D-0014).

  CT2_USE_MKL=0 .venv/Scripts/python src/live.py [--models R-0019-int8,R-0027-int8] [--port 7860]
Then open http://127.0.0.1:7860. Runs on the CPU; listens on this computer only (127.0.0.1).
Models are folders in data/models/: a transformers checkpoint (model.safetensors, loaded in --dtype) or a CTranslate2
copy (model.bin, int8: ct2-transformers-converter --quantization int8; same answers, faster, R-0013). The first model
in --models is the default and is warmed at startup. Other models load on first use and then stay cached.
--threads controls CPU parallelism; --chunk-batch-size bounds the number of 30 s chunks sent to a model at once.

Loop guard (R-0033): a chunk whose text is too repetitive (gzip compression ratio over 2.4, Whisper's own rule) is
decoded again by sampling at temperature 0.2, then 0.4, then 0.6 (best of 5) until the text is no longer repetitive; if
every retry still repeats, the least repetitive text is kept. Normal chunks are never retried, so their beam-5 text and
the token limit are unchanged. --guard-compression-ratio none turns the guard off.
Voice activity filter (R-0033, Neon's pre-flight memo): the server first finds the speech with Silero VAD (the model and
default settings faster-whisper's vad_filter uses), drops the silence (Whisper invents words in silence, R-0023) and
cuts the speech into pieces of at most 30 s at pauses instead of every 30.0 s mid-word. A recording with no speech
gives an empty text without running the model. --no-vad restores the old fixed 30 s cuts.

API (what the page uses; any program can call it the same way):
  POST /transcribe?model=R-0019-int8&also=R-0027-int8&keep=1
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
import zlib
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
CHUNK_BATCH_SIZE = 1  # bound model activations even when an upload contains many chunks
CPU_THREADS = torch.get_num_threads()
dtype = torch.bfloat16
GUARD_RATIO = 2.4  # Whisper's compression-ratio threshold; None turns the loop guard off
GUARD_TEMPERATURES = (0.2, 0.4, 0.6)  # fallback temperatures after the beam search (Neon pre-flight: stop at 0.6)
GUARD_BEST_OF = 5  # samples drawn at each fallback temperature
VAD = False  # library default = fixed 30 s cuts (what the unit tests pin); the server turns it on unless --no-vad

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
            m = ctranslate2.models.Whisper(path, device="cpu", compute_type="int8", intra_threads=CPU_THREADS)
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
    """-> (text, model seconds), using the same bounded path as comparison requests."""
    return transcribe_models(audio, [name])[name]


def compression_ratio(text):
    """gzip-style compression ratio of the text, as Whisper and faster-whisper compute it: loops compress well."""
    data = text.encode("utf-8")
    return len(data) / len(zlib.compress(data)) if data else 0.0


def guarded(text, retry):
    """Whisper's loop guard for one chunk. retry(temperature) decodes the chunk again by sampling and returns its text.
    -> (text, temperature of the kept text, or None when the first text was fine)."""
    if GUARD_RATIO is None or compression_ratio(text) <= GUARD_RATIO:
        return text, None
    tried = [(compression_ratio(text), text, 0.0)]
    for temperature in GUARD_TEMPERATURES:
        new = retry(temperature).strip()
        ratio = compression_ratio(new)
        if ratio <= GUARD_RATIO:
            return new, temperature
        tried.append((ratio, new, temperature))
    _, text, temperature = min(tried, key=lambda x: x[0])  # every retry repeats too: keep the least repetitive
    return text, temperature


def speech_pieces(audio):
    """Silero VAD as faster-whisper runs it: the speech only, in pieces of at most 30 s cut at pauses."""
    from faster_whisper.vad import VadOptions, collect_chunks, get_speech_timestamps

    stamps = get_speech_timestamps(audio, VadOptions(max_speech_duration_s=CHUNK / SR), sampling_rate=SR)
    if not stamps:
        return []
    pieces, _ = collect_chunks(audio, stamps, SR, max_duration=CHUNK / SR)
    return [p for p in pieces if len(p)]


def transcribe_models(audio, names):
    """Bound feature/model batches and reuse compatible features within this request only.

    Chunks are fixed 30 s cuts, or with VAD the speech pieces. Prompt, beam and token limits
    are unchanged; only repetitive chunks are retried (loop guard). Model loading and
    feature extraction also hold the CPU lock, so queued requests cannot do heavy work
    in parallel. compute_seconds retains its original meaning: model generation time.
    """
    if len(audio) == 0:
        raise ValueError("empty audio")
    names = list(dict.fromkeys(names))
    with lock, torch.no_grad():  # one recording at a time; the CPU is the bottleneck anyway
        engines = {name: model(name) for name in names}
        feature_keys = {name: (type(proc.feature_extractor), proc.feature_extractor.to_json_string())
                        for name, (proc, _) in engines.items()}
        texts, seconds = {name: [] for name in names}, dict.fromkeys(names, 0.0)
        every = speech_pieces(audio) if VAD else [audio[i:i + CHUNK] for i in range(0, len(audio), CHUNK)]
        for start in range(0, len(every), CHUNK_BATCH_SIZE):
            pieces = every[start:start + CHUNK_BATCH_SIZE]
            features = {}
            for name, (proc, m) in engines.items():
                key = feature_keys[name]
                if key not in features:
                    features[key] = proc(pieces, sampling_rate=SR, return_tensors="pt").input_features
                feats = features[key]
                t = time.perf_counter()
                if isinstance(m, WhisperForConditionalGeneration):
                    out = m.generate(feats.to(dtype), language="sw", task="transcribe", max_new_tokens=225)

                    def sample(j, temperature):  # one sampled decode of chunk j (the loop guard's retry)
                        ids = m.generate(feats[j:j + 1].to(dtype), language="sw", task="transcribe",
                                         max_new_tokens=225, do_sample=True, temperature=temperature)
                        return proc.batch_decode(ids, skip_special_tokens=True)[0]
                else:
                    import ctranslate2
                    prompt = proc.tokenizer.convert_tokens_to_ids(
                        ["<|startoftranscript|>", "<|sw|>", "<|transcribe|>", "<|notimestamps|>"])
                    res = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats.numpy())),
                                     [prompt] * len(pieces), beam_size=5, max_length=225)
                    out = [r.sequences_ids[0] for r in res]

                    def sample(j, temperature):  # best of GUARD_BEST_OF samples, as faster-whisper retries
                        r = m.generate(ctranslate2.StorageView.from_array(np.ascontiguousarray(feats[j:j + 1].numpy())),
                                       [prompt], beam_size=1, num_hypotheses=GUARD_BEST_OF, sampling_topk=0,
                                       sampling_temperature=temperature, max_length=225)
                        return proc.batch_decode([r[0].sequences_ids[0]], skip_special_tokens=True)[0]
                seconds[name] += time.perf_counter() - t
                for j, text in enumerate(proc.batch_decode(out, skip_special_tokens=True)):
                    t = time.perf_counter()
                    text, temperature = guarded(text.strip(), lambda temp: sample(j, temp))
                    if temperature is not None:  # numbers only: the public demo never logs text
                        seconds[name] += time.perf_counter() - t
                        print(f"loop guard: {name} piece {start + j + 1} of {len(every)} repeated itself; "
                              f"kept the decode at temperature {temperature}", flush=True)
                    texts[name].append(text)
    return {name: (" ".join(texts[name]).strip(), round(seconds[name], 2)) for name in names}


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
                names = [name] + ([also] if also and also != name else [])
                transcriptions = transcribe_models(audio, names)
                text, secs = transcriptions[name]
                rid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                res = {"id": rid, "text": text, "model": name, "audio_seconds": round(len(audio) / SR, 2), "compute_seconds": secs}
                if also and also != name:
                    t2, s2 = transcriptions[also]
                    res["also"] = {"model": also, "text": t2, "compute_seconds": s2}
                if q.get("keep", ["0"])[0] == "1" and not PUBLIC:
                    os.makedirs(KEEP, exist_ok=True)
                    sf.write(os.path.join(KEEP, rid + ".wav"), audio, SR, subtype="PCM_16")
                    log({**res, "file": rid + ".wav"})
                print(f"{name} {res['audio_seconds']} s audio -> {secs} s" + ("" if PUBLIC else f": {text}"
                      + (f"  | {also}: {res['also']['text']}" if "also" in res else "")), flush=True)  # public: no text in logs
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


def positive_int(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="R-0019-int8,R-0027-int8",
                    help="comma-separated folder names in data/models/; the first is the default")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--models-dir", default=MODELS, help="folder holding the model folders (default data/models)")
    ap.add_argument("--public", action="store_true", help="online demo: all addresses, nothing stored")
    ap.add_argument("--threads", type=positive_int, default=CPU_THREADS,
                    help="CPU threads per model (default: PyTorch's CPU thread count)")
    ap.add_argument("--chunk-batch-size", type=positive_int, default=CHUNK_BATCH_SIZE,
                    help="30-second chunks per model call (default 1; larger batches use more memory)")
    ap.add_argument("--guard-compression-ratio", default="2.4",
                    help="loop guard threshold (Whisper's 2.4); 'none' turns the guard off")
    ap.add_argument("--no-vad", action="store_true", help="no voice activity filter: fixed 30 s cuts, silence kept")
    ap.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16",
                    help="for transformers checkpoints: bfloat16 halves memory (medium ~1.9 GB instead of ~3.5 GB)")
    a = ap.parse_args()
    if not FFMPEG:
        sys.exit("ffmpeg not found on PATH (needed to read browser recordings)")
    dtype = getattr(torch, a.dtype)
    CPU_THREADS, CHUNK_BATCH_SIZE = a.threads, a.chunk_batch_size
    GUARD_RATIO = None if a.guard_compression_ratio.lower() == "none" else float(a.guard_compression_ratio)
    if not a.no_vad:
        try:
            import faster_whisper.vad  # noqa: F401  (Silero VAD; needs onnxruntime)
            import onnxruntime  # noqa: F401
        except ImportError as e:
            sys.exit(f"the voice activity filter needs faster-whisper and onnxruntime ({e}); or run with --no-vad")
    torch.set_num_threads(CPU_THREADS)
    MODELS, PUBLIC = a.models_dir, a.public
    offered[:] = [m for m in a.models.split(",") if complete(m)]
    if not offered:
        sys.exit(f"none of {a.models} is in {MODELS}")
    transcribe(np.zeros(SR, dtype=np.float32), offered[0])  # warm only the default; comparisons load lazily
    VAD = not a.no_vad  # switched on after the warm-up: VAD finds no speech in silence and would skip the decode
    host = "0.0.0.0" if PUBLIC else "127.0.0.1"
    print(f"ready: open http://127.0.0.1:{a.port}  (models {', '.join(offered)}; CPU, {CPU_THREADS} threads, batch {CHUNK_BATCH_SIZE}"
          + ("; public: nothing stored" if PUBLIC else "") + ")", flush=True)
    ThreadingHTTPServer((host, a.port), Handler).serve_forever()
