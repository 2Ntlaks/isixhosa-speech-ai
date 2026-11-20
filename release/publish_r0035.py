"""Ship R-0035 as the new whisper-medium-isixhosa (founder's OK, 2026-11-20). Uses the `hf auth login` login.

  python release/publish_r0035.py --dry-run   # list what would change, upload nothing
  python release/publish_r0035.py             # tag the current version R-0019, upload, tag R-0035

One commit replaces the repo's files with R-0035's (same file names as R-0019's): transformers weights at the top
(data/models/R-0035 = S3 models/R-0035, minus training_args.bin), plus tokenizer.json, ct2-int8/ (data/models/R-0035-int8
= S3 models/R-0035-int8, with tokenizer.json, P-0020) and the card release/model-card-medium.md. The old model stays
reachable with revision="R-0019" (and "R-0012").
"""
import argparse
import os

from huggingface_hub import CommitOperationAdd, HfApi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
R0019_SHA = "603a39b5f70526ef2192e5d6f80f713c682a1d39"

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

api = HfApi()
repo = f"{api.whoami()['name']}/whisper-medium-isixhosa"

files = {}  # repo path -> local path
top = os.path.join(DATA, "models", "R-0035")
for f in sorted(os.listdir(top)):
    if f not in ("training_args.bin", "COMPLETE"):
        files[f] = os.path.join(top, f)
ct2 = os.path.join(DATA, "models", "R-0035-int8")
files["tokenizer.json"] = os.path.join(ct2, "tokenizer.json")
for f in sorted(os.listdir(ct2)):
    if f != "COMPLETE":
        files[f"ct2-int8/{f}"] = os.path.join(ct2, f)
card = open(os.path.join(ROOT, "release", "model-card-medium.md"), encoding="utf-8").read()

head = api.model_info(repo).sha
existing = set(api.list_repo_files(repo))
tags = {t.name for t in api.list_repo_refs(repo).tags}
stale = sorted(existing - set(files) - {"README.md", ".gitattributes"})
print(f"repo {repo} at {head}: {len(files)} files to upload "
      f"({sum(os.path.getsize(p) for p in files.values()) / 1e6:.0f} MB) + README.md")
print("files on the Hub not replaced (left as they are):", stale or "none")
print("tags now:", sorted(tags))
for path, local in files.items():
    assert os.path.isfile(local), local
assert head == R0019_SHA or "R-0019" in tags, f"main is {head}, not R-0019 ({R0019_SHA}): stop and look"
if a.dry_run:
    print("dry run: nothing uploaded")
    raise SystemExit
if "R-0019" not in tags:
    api.create_tag(repo, tag="R-0019", revision=R0019_SHA,
                   tag_message="whisper-medium + Swivuriso 146.6 h (R-0019), before the R-0035 recipe")
    print("tagged the current version R-0019")
ops = [CommitOperationAdd(path_in_repo=p, path_or_fileobj=l) for p, l in files.items()]
ops.append(CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=card.encode("utf-8")))
info = api.create_commit(repo, operations=ops,
                         commit_message="R-0035: retrained on 309.7 h with the fixed recipe (9000 steps, SpecAugment)")
api.create_tag(repo, tag="R-0035", revision=info.oid, tag_message="whisper-medium, R-0029 data, fixed recipe (R-0035)")
print("uploaded and tagged R-0035:", info.commit_url)
