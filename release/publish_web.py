"""Publish the in-browser Thetha demo as a free static Hugging Face Space (D-0020). Uses the `hf auth login` login.

  .venv/Scripts/python release/publish_web.py

Uploads release/web/ (index.html, worker.js, README.md) plus transformers.js 3.0.2's transformers.min.js and its ONNX
Runtime wasm, fetched from the npm registry and checked against npm's published sha512. They are served from the Space
itself so the model can use several CPU threads (a worker started from another site cannot be).
"""
import base64
import hashlib
import io
import json
import os
import tarfile
import tempfile
import urllib.request

from huggingface_hub import HfApi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "release", "web")
PKG, VER = "@huggingface/transformers", "3.0.2"
WANT = ("package/dist/transformers.min.js", "package/dist/ort-wasm-simd-threaded.jsep.wasm")

meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/{PKG}/{VER}"))["dist"]
tgz = urllib.request.urlopen(meta["tarball"]).read()
algo, digest = meta["integrity"].split("-", 1)
assert algo == "sha512" and base64.b64encode(hashlib.sha512(tgz).digest()).decode() == digest, "npm checksum mismatch"
print(f"{PKG}@{VER}: checksum matches npm")

api = HfApi()
user = api.whoami()["name"]
sid = f"{user}/thetha"
api.create_repo(sid, repo_type="space", space_sdk="static", exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    with tarfile.open(fileobj=io.BytesIO(tgz)) as t:
        for name in WANT:
            with open(os.path.join(tmp, os.path.basename(name)), "wb") as f:
                f.write(t.extractfile(name).read())
    for f in ("index.html", "worker.js", "README.md"):
        with open(os.path.join(WEB, f), encoding="utf-8") as src, open(os.path.join(tmp, f), "w", encoding="utf-8", newline="\n") as dst:
            dst.write(src.read())
    api.upload_folder(repo_id=sid, repo_type="space", folder_path=tmp, commit_message="Thetha in the browser (D-0020)")
print(f"done: https://huggingface.co/spaces/{sid}")
