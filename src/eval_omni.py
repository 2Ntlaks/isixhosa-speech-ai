"""R-0034: score Meta's Omnilingual ASR CTC models on the project's four test sets, with the same clips and the same
normalisation as every Thetha evaluation (src/testsets.py, src/scoring.py), and time each clip.

  python src/eval_omni.py --model-card omniASR_CTC_1B_v2 --device cuda --batch-size 8 \
      --swivuriso-tsv data/swivuriso_16k/dev_test.tsv --swivuriso-audio data/swivuriso_16k --out out/omni_1b/eval_swivuriso
  python src/eval_omni.py --model-card omniASR_CTC_300M_v2 --device cpu --threads 8 --sample 100 --xml ... --out ...

Models: omniASR_CTC_300M_v2 (325M parameters) and omniASR_CTC_1B_v2 (975M), Apache 2.0, from Meta's official package
(github.com/facebookresearch/omnilingual-asr, installed from a pinned commit in its own venv because it needs fairseq2
and its own torch; see runs/R-0034/run.md). The package downloads the weights from Meta's server on first use.

- No language code is passed: CTC models do not support language conditioning (xho_Latn only matters for the LLM
  variants; --lang passes one anyway).
- The v2 models write capitals, punctuation, digits and curly apostrophes. Curly apostrophes (U+2018, U+2019, U+02BC)
  are mapped to the straight ' before scoring (Thetha only ever writes '), otherwise scoring.normalise would split
  words at them; "hyp_raw" keeps the model's own text and metrics.json also reports the unmapped score. Everything
  else goes through the same scoring.normalise as Thetha (lowercase, punctuation dropped), so a digit where the
  reference spells the number still counts as an error; metrics.json "diagnostics" adds the FLEURS clips whose
  reference has no digit, CER without spaces, and how many outputs contain digits or non-ASCII letters.
- The package refuses audio over 40 s; every test clip here is at most 30 s (the same --max-seconds as Thetha).
- Timing: on CPU each clip goes alone (batch 1), so seconds per clip is the model's own time on this machine
  (warm-up excluded, audio loading excluded). With --batch-size > 1 (GPU, accuracy runs) the batch time is shared
  equally over its clips and only the total is meaningful.
--dry-run uses a stand-in model that returns the reference text (tests the plumbing without the package).
"""
import argparse
import math
import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import testsets  # noqa: E402

OMNI_REPO = "https://github.com/facebookresearch/omnilingual-asr"
CURLY = str.maketrans({"‘": "'", "’": "'", "ʼ": "'"})  # typographic apostrophes -> the one Thetha writes


def load_pipeline(card, device, dtype):
    import torch
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

    return ASRInferencePipeline(model_card=card, device=device, dtype=getattr(torch, dtype))


class DryRun:
    """Stands in for ASRInferencePipeline: answers with the reference text (set by the caller per clip)."""

    def __init__(self):
        self.answers = []

    def transcribe(self, inp, lang=None, batch_size=1):
        assert all(x["sample_rate"] == 16000 and x["waveform"].ndim == 1 for x in inp)
        assert lang is None or len(lang) == len(inp)
        out, self.answers = self.answers[: len(inp)], self.answers[len(inp):]
        return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    testsets.add_args(ap)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-card", default="omniASR_CTC_300M_v2",
                    help="omniASR_CTC_300M_v2 | omniASR_CTC_1B_v2 (any card the package knows)")
    ap.add_argument("--lang", default="", help="language code for the package (default none: CTC models ignore it)")
    ap.add_argument("--keep-curly-apostrophes", action="store_true", help="score the raw output (no ' mapping)")
    ap.add_argument("--device", default="cpu", help="cpu | cuda")
    ap.add_argument("--dtype", default=None, help="float32 | bfloat16 | float16 (default: float32 on CPU, "
                    "bfloat16 on GPU, the package's own default there)")
    ap.add_argument("--threads", type=int, default=8, help="CPU threads (torch.set_num_threads)")
    ap.add_argument("--batch-size", type=int, default=1, help="1 for per-clip timing; larger on a GPU")
    ap.add_argument("--max-audio-seconds", type=float, default=40.0, help="the package's own limit")
    ap.add_argument("--package-commit", default=os.environ.get("OMNI_COMMIT", ""), help="recorded in metrics.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dtype = a.dtype or ("float32" if a.device == "cpu" else "bfloat16")

    kind, clips, too_long = testsets.load(a)
    over = [c["id"] for c in clips if c["duration"] > a.max_audio_seconds]
    if over:
        raise SystemExit(f"{len(over)} clips are over {a.max_audio_seconds} s, which the package refuses: {over[:3]}")

    env = {"device": a.device, "dtype": dtype, "python": platform.python_version(),
           "machine": platform.processor() or platform.machine()}
    if a.dry_run:
        pipe = DryRun()
        env["engine"] = "dry run (reference text)"
    else:
        import importlib.metadata as md

        import torch
        torch.set_num_threads(a.threads)
        pipe = load_pipeline(a.model_card, a.device, dtype)
        env.update({"engine": f"omnilingual-asr {md.version('omnilingual-asr')}, fairseq2 {md.version('fairseq2')}, "
                              f"torch {torch.__version__}", "cpu_threads": torch.get_num_threads(),
                    "package": f"{OMNI_REPO}@{a.package_commit}" if a.package_commit else OMNI_REPO})
        if a.device == "cuda":
            env["gpu"] = torch.cuda.get_device_name(0)
        pipe.transcribe([{"waveform": testsets.read16k(clips[0]["path"]), "sample_rate": 16000}],
                        lang=[a.lang] if a.lang else None, batch_size=1)  # warm-up, not timed
    lang = a.lang or None

    order = list(range(len(clips)))
    if a.batch_size > 1:
        order.sort(key=lambda i: clips[i]["duration"])  # similar lengths pad less
    t0 = time.time()
    for k in range(0, len(order), a.batch_size):
        batch = [clips[i] for i in order[k: k + a.batch_size]]
        inp = [{"waveform": testsets.read16k(c["path"]), "sample_rate": 16000} for c in batch]
        if a.dry_run:
            pipe.answers = [c["text"] for c in batch]
        start = time.perf_counter()
        hyps = pipe.transcribe(inp, lang=[lang] * len(batch) if lang else None, batch_size=len(batch))
        each = (time.perf_counter() - start) / len(batch)
        for c, h in zip(batch, hyps):
            c["hyp_raw"] = h.strip()
            c["hyp"] = c["hyp_raw"] if a.keep_curly_apostrophes else c["hyp_raw"].translate(CURLY)
            c["lang"], c["seconds"] = lang or "-", round(each, 3)
        done = k + len(batch)
        if done % 100 < a.batch_size or done == len(clips):
            print(f"  {done}/{len(clips)} clips, {time.time() - t0:.0f} s", flush=True)
    secs = time.time() - t0

    per_clip = [c["seconds"] for c in clips]
    timing = {"batch_size": a.batch_size,
              "seconds_per_clip_mean": round(statistics.mean(per_clip), 3),
              "seconds_per_clip_median": round(statistics.median(per_clip), 3),
              "seconds_per_clip_p95": round(sorted(per_clip)[math.ceil(0.95 * len(per_clip)) - 1], 3),
              "real_time_factor": round(sum(per_clip) / sum(c["duration"] for c in clips), 4),
              "note": "model time per clip, warm-up and audio loading excluded"
                      + ("" if a.batch_size == 1 else "; batch time shared equally, only the total is meaningful")}
    from scoring import score
    raw = score([c["text"] for c in clips], [c["hyp_raw"] for c in clips])
    metrics = testsets.report(
        a, kind, clips, too_long, model=a.model_card, language=f"{a.lang} (ignored by CTC models)" if a.lang else "none",
        max_new_tokens=None, seconds=secs, env=env, column="lang code", output_column="output",
        extra={"decoder": "Meta Omnilingual ASR CTC, greedy (argmax) as in the package",
               "sample": {"n": a.sample, "seed": a.sample_seed} if a.sample else None, "timing": timing,
               "curly_apostrophes_mapped": not a.keep_curly_apostrophes,
               "score_without_apostrophe_mapping": {"wer": round(raw["wer"], 2), "cer": round(raw["cer"], 2)},
               "outputs_with_curly_apostrophes": sum(c["hyp_raw"] != c["hyp"] for c in clips),
               "diagnostics": testsets.diagnostics(kind, clips)})
    print({k: metrics[k] for k in ("wer", "cer", "exact_match_pct", "seconds")}, timing, flush=True)


if __name__ == "__main__":
    main()
