"""Download the 8-bit models from the Hub, then start Thetha in public mode (nothing stored)."""
import os
import shutil
import subprocess
import sys

from huggingface_hub import snapshot_download

OWNER = "{HF_USER}"
MODELS = {"R-0012-int8": "whisper-medium-isixhosa", "R-0007-int8": "whisper-small-isixhosa"}  # medium is the default
os.makedirs("models", exist_ok=True)
for name, repo in MODELS.items():
    if not os.path.isdir(os.path.join("models", name)):
        tmp = snapshot_download(f"{OWNER}/{repo}", allow_patterns=["ct2-int8/*"], local_dir=os.path.join("dl", repo))
        shutil.move(os.path.join(tmp, "ct2-int8"), os.path.join("models", name))
sys.exit(subprocess.call([sys.executable, "src/live.py", "--public", "--models-dir", "models",
                          "--models", ",".join(MODELS), "--port", "7860"]))
