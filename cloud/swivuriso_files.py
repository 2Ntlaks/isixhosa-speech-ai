"""Prepare a Swivuriso (isiXhosa) fetch job: file list with sizes and sha256, pinned revision, and the founder's token.

    python cloud/swivuriso_files.py <out_dir>

Called by cloud/fetch_data.sh. Writes files.tsv (path, size, sha256 or "-"), revision.txt and hf_token into out_dir.
Fails if the founder's Hugging Face account cannot read the gated dataset.
"""
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download

REPO = "dsfsi-anv/za-african-next-voices"

out = Path(sys.argv[1])
token = get_token()
if not token:
    sys.exit("no Hugging Face token on this machine (hf auth login)")
api = HfApi(token=token)
info = api.dataset_info(REPO, files_metadata=True)
# access check: listing works without accepting the terms, downloading does not
hf_hub_download(REPO, "dev/xho/meta.csv", repo_type="dataset", revision=info.sha, token=token,
                local_dir=out / "check")

rows = []
for s in info.siblings:
    if "xho" not in s.rfilename.split("/"):
        continue
    sha = s.lfs.sha256 if s.lfs else "-"
    rows.append(f"{s.rfilename}\t{s.size}\t{sha}")
rows.sort()
(out / "files.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
(out / "revision.txt").write_text(info.sha, encoding="utf-8", newline="")
(out / "hf_token").write_text(token, encoding="utf-8", newline="")
total = sum(int(r.split("\t")[1]) for r in rows)
print(f"== Swivuriso isiXhosa @ {info.sha[:12]}: {len(rows)} files, {total / 1e9:.1f} GB")
