"""Publish the models and the Thetha demo to Hugging Face (D-0019). Uses the login from `hf auth login`.

  .venv/Scripts/python release/publish.py --dry-run     # check every file, upload nothing
  .venv/Scripts/python release/publish.py               # both model repos

Model repos (public): <user>/whisper-medium-isixhosa (R-0012) and <user>/whisper-small-isixhosa (R-0007), each with the
transformers weights at the top and the 8-bit CTranslate2 copy in ct2-int8/. The demo (a static Space running the model in
the browser) is published by release/publish_web.py: Docker Spaces need a paid plan (P-0014, D-0020).
Re-running is safe: repos that exist are reused and only changed files are uploaded.
"""
import argparse
import os
import sys

from huggingface_hub import HfApi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = os.path.join(ROOT, "release")
MODELS = os.path.join(ROOT, "data", "models")
RELEASES = [  # (run, repo name, card)
    ("R-0012", "whisper-medium-isixhosa", "model-card-medium.md"),
    ("R-0007", "whisper-small-isixhosa", "model-card-small.md"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--user", help="Hugging Face user (default: whoever is logged in)")
a = ap.parse_args()

api = HfApi()
if a.user:
    user = a.user
else:
    try:
        user = api.whoami()["name"]
    except Exception:
        if not a.dry_run:
            sys.exit("not logged in: run `hf auth login` first")
        user = "<user>"
space_url = "https://ntlakanipho-thetha.static.hf.space"
fill = lambda s: s.replace("{HF_USER}", user).replace("{SPACE_URL}", space_url)


def size(path):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)


# 1. check everything first
for run, repo, card in RELEASES:
    full, int8 = os.path.join(MODELS, run), os.path.join(MODELS, run + "-int8")
    for need in (os.path.join(full, "model.safetensors"), os.path.join(int8, "model.bin"), os.path.join(REL, card)):
        if not os.path.isfile(need):
            sys.exit(f"missing {need}")
    print(f"{user}/{repo}: {run} {size(full) / 1e9:.2f} GB + ct2-int8 {size(int8) / 1e9:.2f} GB")
if a.dry_run:
    print("dry run: nothing uploaded")
    sys.exit(0)

# 2. models
for run, repo, card in RELEASES:
    rid = f"{user}/{repo}"
    api.create_repo(rid, repo_type="model", exist_ok=True)
    print(f"uploading {rid} ... (large: this can take a while)", flush=True)
    api.upload_folder(repo_id=rid, folder_path=os.path.join(MODELS, run), commit_message=f"{run} weights")
    api.upload_folder(repo_id=rid, folder_path=os.path.join(MODELS, run + "-int8"), path_in_repo="ct2-int8",
                      commit_message=f"{run} 8-bit CTranslate2 copy")
    api.upload_file(path_or_fileobj=fill(open(os.path.join(REL, card), encoding="utf-8").read()).encode(),
                    path_in_repo="README.md", repo_id=rid, commit_message="Model card")
    print(f"done: https://huggingface.co/{rid}", flush=True)
print("models done; the demo is published by release/publish_web.py (D-0020)")
