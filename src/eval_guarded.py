"""R-0033: score a Whisper fine-tune with Whisper's own reliability rules (faster-whisper on CTranslate2), on exactly
the clips and normalisation of every earlier evaluation (src/testsets.py, src/scoring.py).

  # cloud GPU, fp16: the published R-0019 at a pinned revision, converted from its full weights
  python src/eval_guarded.py --hf-repo Ntlakanipho/whisper-medium-isixhosa --revision <sha> --hf-variant full \
      --device cuda --compute-type float16 --fleurs-tsv data/fleurs_xh_za/test.tsv \
      --fleurs-audio data/fleurs_xh_za/audio/test --train-fleurs-tsv data/fleurs_xh_za/train.tsv --out out/eval_fleurs
  # CPU, int8: the published int8 copy (what the live page and Siyamthanda run), 100 seeded clips, timed
  python src/eval_guarded.py --hf-repo ... --revision <sha> --hf-variant ct2-int8 --device cpu --compute-type int8 \
      --threads 8 --sample 100 --xml ... --out ...
  # a local model: a CTranslate2 folder, or a transformers checkpoint (converted with --quantization first)
  python src/eval_guarded.py --model model/final --quantization float16 --device cuda ...

What "Whisper's reliability rules" means (Radford et al. 2022, section 4.5; faster-whisper's defaults): decode with
beam search (5); if the text is too repetitive (gzip compression ratio > 2.4) or the model is unsure (average log
probability < -1.0), decode again by sampling at temperature 0.2, then 0.4, ... up to 1.0 (best of 5 samples); if the
model says "no speech" (probability > 0.6) while unsure, output nothing. Each clip is decoded on its own, with no
previous text and no timestamps, language "sw" (isiXhosa borrows Swahili's tag, D-0007). Every setting is a flag.
Sampling is seeded per clip (from the clip id), so a rerun gives the same text whatever the order or batch.

Writes predictions.jsonl, metrics.json and samples.md (src/compare_runs.py compares them with earlier runs). Besides
WER/CER it reports how many clips needed a retry ("fallback"), at which temperature they ended, how many exhausted
every temperature, how many were dropped as "no speech", and the time per clip.
"""
import argparse
import math
import os
import platform
import statistics
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(__file__))
import make_ct2  # noqa: E402
import testsets  # noqa: E402


def float_or_none(value):
    return None if str(value).lower() in ("none", "off") else float(value)


def add_decode_args(ap):
    g = ap.add_argument_group("decoding (defaults = Whisper's reliability rules)")
    g.add_argument("--language", default="sw")
    g.add_argument("--task", default="transcribe")
    g.add_argument("--beam-size", type=int, default=5)
    g.add_argument("--best-of", type=int, default=5, help="samples drawn at each fallback temperature")
    g.add_argument("--patience", type=float, default=1.0)
    g.add_argument("--length-penalty", type=float, default=1.0)
    g.add_argument("--repetition-penalty", type=float, default=1.0)
    g.add_argument("--no-repeat-ngram-size", type=int, default=0)
    g.add_argument("--temperatures", default="0.0,0.2,0.4,0.6,0.8,1.0",
                   help="tried in order; the first is the beam search, the rest are fallbacks")
    g.add_argument("--compression-ratio-threshold", type=float_or_none, default=2.4, help="'none' turns it off")
    g.add_argument("--log-prob-threshold", type=float_or_none, default=-1.0, help="'none' turns it off")
    g.add_argument("--no-speech-threshold", type=float_or_none, default=0.6, help="'none' turns it off")
    g.add_argument("--condition-on-previous-text", action="store_true", help="default off: every clip on its own")
    g.add_argument("--with-timestamps", action="store_true", help="default off: without_timestamps=True")
    g.add_argument("--no-suppress-blank", action="store_true")
    g.add_argument("--vad-filter", action="store_true", help="Silero voice-activity filter (default off)")
    g.add_argument("--max-new-tokens", type=int, default=None,
                   help=f"default: the limit earlier runs used for this test set {testsets.DEFAULT_MAX_NEW_TOKENS}")


def decode_options(a, kind):
    temps = tuple(float(t) for t in a.temperatures.split(","))
    return {
        "language": a.language, "task": a.task, "beam_size": a.beam_size, "best_of": a.best_of,
        "patience": a.patience, "length_penalty": a.length_penalty, "repetition_penalty": a.repetition_penalty,
        "no_repeat_ngram_size": a.no_repeat_ngram_size, "temperature": temps,
        "compression_ratio_threshold": a.compression_ratio_threshold, "log_prob_threshold": a.log_prob_threshold,
        "no_speech_threshold": a.no_speech_threshold, "condition_on_previous_text": a.condition_on_previous_text,
        "without_timestamps": not a.with_timestamps, "suppress_blank": not a.no_suppress_blank,
        "vad_filter": a.vad_filter, "word_timestamps": False, "initial_prompt": None,
        "max_new_tokens": a.max_new_tokens or testsets.DEFAULT_MAX_NEW_TOKENS[kind],
    }


class AttemptLog:
    """Stands in for faster-whisper's CTranslate2 model: passes every call through and records each decoding
    attempt (one generate() call = one try at one temperature), so the fallbacks can be counted per clip."""

    def __init__(self, model):
        self._model = model
        self.attempts = []

    def __getattr__(self, name):
        return getattr(self._model, name)

    def generate(self, *args, **kwargs):
        results = self._model.generate(*args, **kwargs)
        r = results[0]
        tokens = r.sequences_ids[0]
        lp = kwargs.get("length_penalty", 1.0)
        self.attempts.append({
            "temperature": float(kwargs.get("sampling_temperature", 0.0)),
            "tokens": tokens,
            "avg_logprob": r.scores[0] * (len(tokens) ** lp) / (len(tokens) + 1),  # as faster-whisper computes it
            "no_speech_prob": getattr(r, "no_speech_prob", 0.0),
        })
        return results


def needs_retry(attempt, opts):
    """faster-whisper's rule (transcribe.py generate_with_fallback), applied to one recorded attempt."""
    retry = False
    if opts["compression_ratio_threshold"] is not None and attempt["compression_ratio"] > opts["compression_ratio_threshold"]:
        retry = True
    if opts["log_prob_threshold"] is not None and attempt["avg_logprob"] < opts["log_prob_threshold"]:
        retry = True
        if opts["no_speech_threshold"] is not None and attempt["no_speech_prob"] > opts["no_speech_threshold"]:
            retry = False  # silence, not a failure
    return retry


def load_model(a):
    """-> (faster_whisper.WhisperModel, description of where the weights came from)."""
    from faster_whisper import WhisperModel

    if a.hf_repo:
        folder = make_ct2.fetch(a.hf_repo, a.revision, a.hf_variant, a.cache, a.quantization)
        source = {"hf_repo": a.hf_repo, "revision": a.revision, "variant": a.hf_variant,
                  **({"converted_to": a.quantization} if a.hf_variant == "full" else {})}
    elif os.path.isfile(os.path.join(a.model, "model.bin")):
        folder = make_ct2.check(a.model)
        source = {"ct2_folder": a.model}
    else:  # a transformers checkpoint (e.g. a training run's model/final): convert once, next to the cache
        folder = make_ct2.convert(a.model, os.path.join(a.cache, os.path.basename(os.path.normpath(a.model))
                                                        + f"-ct2-{a.quantization}"), a.quantization)
        source = {"transformers_folder": a.model, "converted_to": a.quantization}
    model = WhisperModel(folder, device=a.device, compute_type=a.compute_type, cpu_threads=a.threads,
                         num_workers=1, local_files_only=True)
    return model, {**source, "folder": folder}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    testsets.add_args(ap)
    ap.add_argument("--out", required=True)
    m = ap.add_argument_group("model")
    m.add_argument("--model", help="local CTranslate2 folder, or a transformers checkpoint folder (converted)")
    m.add_argument("--hf-repo", help="instead of --model: a Hugging Face model repo")
    m.add_argument("--revision", help="full commit hash of --hf-repo (pinned)")
    m.add_argument("--hf-variant", choices=["ct2-int8", "full"], default="ct2-int8")
    m.add_argument("--quantization", default="float16", help="conversion type for a full / transformers model")
    m.add_argument("--cache", default="data/models_cache")
    m.add_argument("--device", default="cpu", help="cpu | cuda")
    m.add_argument("--compute-type", default="int8", help="int8 (CPU) | float16 (GPU) | ...")
    m.add_argument("--threads", type=int, default=8, help="CPU threads (CPU device)")
    m.add_argument("--label", help="model name written in metrics.json (default: repo@revision or folder)")
    add_decode_args(ap)
    a = ap.parse_args()
    if bool(a.model) == bool(a.hf_repo):
        ap.error("give exactly one of --model or --hf-repo")
    if a.hf_repo and not a.revision:
        ap.error("--hf-repo needs --revision (a full commit hash)")

    import ctranslate2
    import faster_whisper
    from faster_whisper.transcribe import get_compression_ratio

    kind, clips, too_long = testsets.load(a)
    opts = decode_options(a, kind)
    model, source = load_model(a)
    log = AttemptLog(model.model)
    model.model = log  # every decoding attempt now passes through the log
    eot = model.hf_tokenizer.token_to_id("<|endoftext|>")
    temps = opts["temperature"]
    label = a.label or (f"{a.hf_repo}@{a.revision[:8]} ({a.hf_variant})" if a.hf_repo else a.model)
    print(f"model {label} on {a.device} ({a.compute_type}); {len(clips)} clips; decoding {opts}", flush=True)

    t0 = time.time()
    for i, c in enumerate(clips):
        audio = testsets.read16k(c["path"])
        ctranslate2.set_random_seed((zlib.crc32(c["id"].encode()) + a.seed) % 2 ** 31)
        log.attempts.clear()
        start = time.perf_counter()
        segments, _ = model.transcribe(audio, **opts)
        segments = list(segments)  # faster-whisper decodes lazily: the work happens here
        c["seconds"] = round(time.perf_counter() - start, 3)
        c["hyp"] = " ".join(s.text.strip() for s in segments).strip()
        c["lang"] = a.language
        for att in log.attempts:
            att["compression_ratio"] = get_compression_ratio(
                model.hf_tokenizer.decode([t for t in att.pop("tokens") if t < eot]).strip())
        tried = [att["temperature"] for att in log.attempts]
        c["decode"] = {
            "attempts": len(tried), "temperatures_tried": tried,
            "final_temperature": segments[-1].temperature if segments else None,
            "fallback": len(tried) > 1,
            "exhausted": len(tried) >= len(temps) and bool(log.attempts) and needs_retry(log.attempts[-1], opts),
            "no_speech_skip": not segments,
            "avg_logprob": round(segments[-1].avg_logprob, 3) if segments else None,
            "compression_ratio": round(segments[-1].compression_ratio, 3) if segments else None,
            "no_speech_prob": round(log.attempts[-1]["no_speech_prob"], 3) if log.attempts else None,
        }
        if (i + 1) % 50 == 0 or i + 1 == len(clips):
            fb = sum(x["decode"]["fallback"] for x in clips[: i + 1])
            print(f"  {i + 1}/{len(clips)} clips, {time.time() - t0:.0f} s, {fb} needed a fallback", flush=True)
    secs = time.time() - t0

    per_clip = [c["seconds"] for c in clips]
    finals = {}
    for c in clips:
        if c["decode"]["fallback"]:
            k = "no speech" if c["decode"]["no_speech_skip"] else str(c["decode"]["final_temperature"])
            finals[k] = finals.get(k, 0) + 1
    guard = {
        "clips_with_fallback": sum(c["decode"]["fallback"] for c in clips),
        "fallback_pct": round(100 * sum(c["decode"]["fallback"] for c in clips) / len(clips), 2),
        "fallback_final_temperature": dict(sorted(finals.items())),
        "exhausted_every_temperature": sum(c["decode"]["exhausted"] for c in clips),
        "no_speech_skipped": sum(c["decode"]["no_speech_skip"] for c in clips),
        "fallback_clip_ids": [c["id"] for c in clips if c["decode"]["fallback"]],
        "decoding_attempts": sum(c["decode"]["attempts"] for c in clips),
    }
    timing = {"seconds_per_clip_mean": round(statistics.mean(per_clip), 3),
              "seconds_per_clip_median": round(statistics.median(per_clip), 3),
              "seconds_per_clip_p95": round(sorted(per_clip)[math.ceil(0.95 * len(per_clip)) - 1], 3),
              "real_time_factor": round(sum(per_clip) / sum(c["duration"] for c in clips), 4),
              "note": "decode time per clip (features + encoder + decoder), audio loading excluded"}
    settings = {k: (list(v) if isinstance(v, tuple) else v) for k, v in opts.items()}
    env = {"engine": f"faster-whisper {faster_whisper.__version__}, ctranslate2 {ctranslate2.__version__}",
           "device": a.device, "compute_type": a.compute_type, "cpu_threads": a.threads,
           "mkl": os.environ.get("CT2_USE_MKL", "default"), "python": platform.python_version(),
           "machine": platform.processor() or platform.machine()}
    if a.device == "cuda":
        import subprocess
        env["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                                    text=True).stdout.strip()
    metrics = testsets.report(
        a, kind, clips, too_long, model=label, language=a.language, max_new_tokens=opts["max_new_tokens"],
        seconds=secs, env=env, column="language", output_column="output",
        extra={"decoder": "faster-whisper with Whisper's reliability rules (R-0033)", "decoding": settings,
               "model_source": source, "sample": {"n": a.sample, "seed": a.sample_seed} if a.sample else None,
               "guard": guard, "timing": timing})
    print({k: metrics[k] for k in ("wer", "cer", "exact_match_pct", "seconds")}, guard["clips_with_fallback"],
          "fallbacks", timing, flush=True)


if __name__ == "__main__":
    main()
