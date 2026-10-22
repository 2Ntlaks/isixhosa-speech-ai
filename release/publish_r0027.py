"""Ship R-0027 as the new whisper-small-isixhosa (the model the browser demo runs). Uses the `hf auth login` login.

  .venv/Scripts/python release/publish_r0027.py --dry-run   # list what would change, upload nothing
  .venv/Scripts/python release/publish_r0027.py             # tag the old version R-0007, upload, tag R-0027

One commit replaces every file of the repo with R-0027's (same file names as R-0007's): transformers weights at the top,
ct2-int8/ (data/models/R-0027-int8, R-0028), onnx/ (data/onnx/R-0027, src/export_onnx.py, R-0028) and the card
release/model-card-small.md. The old model stays reachable with revision="R-0007". The demo then pins revision R-0027
(release/web/worker.js) so browsers that cached R-0007 fetch the new files; republish it with release/publish_web.py.
"""
import argparse
import os

from huggingface_hub import CommitOperationAdd, HfApi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SPACE_URL = "https://ntlakanipho-thetha.static.hf.space/index.html"

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

api = HfApi()
user = api.whoami()["name"]
repo = f"{user}/whisper-small-isixhosa"

files = {}  # repo path -> local path
top = os.path.join(DATA, "models", "R-0027")
for f in sorted(os.listdir(top)):
    if f != "training_args.bin":
        files[f] = os.path.join(top, f)
files["tokenizer.json"] = os.path.join(DATA, "onnx", "R-0027", "tokenizer.json")
ct2 = os.path.join(DATA, "models", "R-0027-int8")
for f in sorted(os.listdir(ct2)):
    files[f"ct2-int8/{f}"] = os.path.join(ct2, f)
for f in ("encoder_model_quantized.onnx", "decoder_model_merged_quantized.onnx"):
    files[f"onnx/{f}"] = os.path.join(DATA, "onnx", "R-0027", f)
card = open(os.path.join(ROOT, "release", "model-card-small.md"), encoding="utf-8").read()
card = card.replace("{HF_USER}", user).replace("{SPACE_URL}", SPACE_URL)

existing = set(api.list_repo_files(repo))
tags = {t.name for t in api.list_repo_refs(repo).tags}
stale = sorted(existing - set(files) - {"README.md", ".gitattributes"})
print(f"repo {repo}: {len(files)} files to upload ({sum(os.path.getsize(p) for p in files.values()) / 1e6:.0f} MB) + README.md")
print("files on the Hub not replaced (left as they are):", stale or "none")
print("tags now:", sorted(tags))
for path, local in files.items():
    assert os.path.isfile(local), local
if a.dry_run:
    print("dry run: nothing uploaded")
    raise SystemExit
if "R-0007" not in tags:
    api.create_tag(repo, tag="R-0007", tag_message="whisper-small, NCHLT + FLEURS (R-0007), before Swivuriso")
    print("tagged the current version R-0007")
ops = [CommitOperationAdd(path_in_repo=p, path_or_fileobj=l) for p, l in files.items()]
ops.append(CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=card.encode("utf-8")))
info = api.create_commit(repo, operations=ops, commit_message="R-0027: retrained with Swivuriso (245 h incl. long-clip pieces)")
api.create_tag(repo, tag="R-0027", revision=info.oid, tag_message="whisper-small + Swivuriso incl. long-clip pieces (R-0027)")
print("uploaded and tagged R-0027:", info.commit_url)
