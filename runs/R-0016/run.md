# R-0016 · Stage 4: R-0015 plus stitched isiXhosa + English clips

- **Why:** English alone (R-0015) teaches English spelling, but never inside an isiXhosa sentence. Stitched clips put
  both languages in one clip under the isiXhosa tag, the closest we can get to code-switching with open data (D-0017).
- **What:** exactly R-0015 plus `--stitch 8000`: 8000 clips, each a real NCHLT isiXhosa clip and a real NCHLT English
  clip joined (patterns x+e, e+x, x+e+x, 0.1-0.4 s silence between), seed 42. Transcripts are the corpora's own,
  joined in order; nothing is invented. Which clips were joined is saved (stitched.jsonl).
- **Known limit:** real code-switching often happens inside a word (i_ grapefruit = igrapefruit) and with one speaker;
  stitched clips switch only between phrases and change speaker at the join.
- **Same node, job and scoring as R-0015** (runs/R-0015/job.sh).
