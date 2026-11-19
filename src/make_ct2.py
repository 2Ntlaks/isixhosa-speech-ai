"""Make a CTranslate2 copy of a Whisper model that faster-whisper and src/live.py can load, or fetch a published one.

  python src/make_ct2.py convert --model model/final --out models/R-0035-int8 --quantization int8
  python src/make_ct2.py fetch --repo Ntlakanipho/whisper-medium-isixhosa --revision 603a39b5... --variant ct2-int8 \
      --cache data/models_cache

A CTranslate2 copy = the converter's output (config.json, model.bin, vocabulary.json) + the full model's audio and
tokenizer settings files + tokenizer.json (faster-whisper needs it). The converter writes only the first three, which
is how R-0031's first attempt failed (P-0020); this script always adds the rest and checks they are there.
"""
import argparse
import os
import shutil
import sys

# Copied from the full model into every CTranslate2 copy (P-0020). config.json is NOT copied: the converter's differs.
PROCESSOR_FILES = ["added_tokens.json", "generation_config.json", "merges.txt", "normalizer.json",
                   "preprocessor_config.json", "special_tokens_map.json", "tokenizer_config.json", "vocab.json"]
NEEDED = ["config.json", "model.bin", "vocabulary.json", "preprocessor_config.json", "tokenizer.json"]


def add_tokenizer_json(folder):
    """faster-whisper reads tokenizer.json; build it from the folder's own tokenizer files if it is missing."""
    path = os.path.join(folder, "tokenizer.json")
    if not os.path.isfile(path):
        from transformers import WhisperTokenizerFast
        WhisperTokenizerFast.from_pretrained(folder).backend_tokenizer.save(path)
    return path


def check(folder):
    missing = [f for f in NEEDED if not os.path.isfile(os.path.join(folder, f))]
    if missing:
        raise SystemExit(f"{folder} is not a complete CTranslate2 Whisper copy: missing {missing} (P-0020)")
    return folder


def convert(src, out, quantization):
    """Transformers Whisper checkpoint folder -> CTranslate2 folder (quantization: int8, float16, int8_float16, ...)."""
    import ctranslate2

    if os.path.isfile(os.path.join(out, "model.bin")) and os.path.isfile(os.path.join(out, "tokenizer.json")):
        return check(out)
    add_tokenizer_json(src)
    copy = [f for f in PROCESSOR_FILES + ["tokenizer.json"] if os.path.isfile(os.path.join(src, f))]
    ctranslate2.converters.TransformersConverter(src, copy_files=copy).convert(out, quantization=quantization,
                                                                               force=True)
    return check(out)


def fetch(repo, revision, variant, cache, quantization="float16"):
    """A model published on Hugging Face, at a pinned revision, as a local CTranslate2 folder.
    variant ct2-int8: the published int8 copy (what the live page and Siyamthanda run).
    variant full: the full weights, converted here with `quantization` (float16 for a GPU)."""
    from huggingface_hub import snapshot_download

    if len(revision) < 40:
        raise SystemExit(f"pin a full commit hash, not {revision!r}: the model must not change under a run")
    name = f"{repo.split('/')[-1]}@{revision[:8]}"
    if variant == "ct2-int8":
        local = os.path.join(cache, name)
        snapshot_download(repo, revision=revision, allow_patterns=["ct2-int8/*"], local_dir=local)
        folder = os.path.join(local, "ct2-int8")
        add_tokenizer_json(folder)
        return check(folder)
    if variant != "full":
        raise SystemExit(f"unknown variant {variant}")
    src = os.path.join(cache, name + "-full")
    snapshot_download(repo, revision=revision, allow_patterns=["*.json", "*.txt", "model.safetensors"],
                      ignore_patterns=["ct2-int8/*", "onnx/*"], local_dir=src)
    return convert(src, os.path.join(cache, f"{name}-ct2-{quantization}"), quantization)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--model", required=True, help="transformers checkpoint folder (model.safetensors + processor)")
    c.add_argument("--out", required=True)
    c.add_argument("--quantization", default="int8")
    f = sub.add_parser("fetch")
    f.add_argument("--repo", required=True)
    f.add_argument("--revision", required=True)
    f.add_argument("--variant", choices=["ct2-int8", "full"], default="ct2-int8")
    f.add_argument("--quantization", default="float16", help="for --variant full")
    f.add_argument("--cache", default="data/models_cache")
    a = ap.parse_args()
    if a.cmd == "convert":
        if os.path.exists(a.out):
            shutil.rmtree(a.out)
        print(convert(a.model, a.out, a.quantization))
    else:
        print(fetch(a.repo, a.revision, a.variant, a.cache, a.quantization))


if __name__ == "__main__":
    sys.exit(main())
