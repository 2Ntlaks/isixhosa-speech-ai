`# R-0024 · Fast-speech diagnosis: is "man ukuya" -> "amanye" about speed? (laptop, $0)
`
`- **Why:** step 3 of the combined plan. Claude had guessed that fast speech is the cause and more fast training speech the
`  fix; Codex asked to test that before spending. Two parts, both on the laptop with existing data.
`- **Part 1, done 21 Oct (no new decoding):** R-0019's Swivuriso test predictions (2,145 clips, runs/R-0019/eval_swivuriso,
`  gitignored), split into quarters by speaking speed (letters per second of the normalised reference). Only counts below.
`
`  | Quarter (letters/s) | median words/s | unscripted share | CER % | WER % |
`  |---|---|---|---|---|
`  | slowest (1.6-7.4) | 0.88 | 30 % | 4.49 | 19.69 |
`  | 7.4-8.4 | 1.07 | 21 % | 3.58 | 17.29 |
`  | 8.4-9.6 | 1.20 | 31 % | 3.62 | 17.91 |
`  | fastest (9.6+) | 1.44 | 53 % | 4.73 | 21.10 |
`
`  Unscripted clips only: slower half CER 3.71 / WER 17.81, faster half 4.41 / 19.84. Scripted: 4.18 / 18.64 vs 4.11 / 19.69.
`  Reading: speed costs something (about +0.7 to +1.1 CER points for the fastest speech) but it is not a cliff, and the
`  slowest quarter is also worse (likely pauses and hesitations). The founder's recording 20261021-135703 runs at about
`  9 letters/s by R-0019's own output (exact text not known), which is ordinary for Swivuriso. So speed alone is a weak
`  explanation for "amanye". Recording level: peak 0.45, no clipping, RMS -39 dBFS (quiet).
`- **Part 2 (planned):** \`runs/R-0024/variants.py\`: decode that recording as original, louder, slowed 0.9x and 0.8x
`  (pitch kept), cut to its first 4 s and 3 s, and with 0.5 s of silence before; R-0019-int8 and R-0012-int8, beam 5,
`  5 candidates each. Question: which change, if any, brings back "man ukuya" (the founder's words). One recording, so
`  this gives clues, not proof.
`- **Command:** \`CT2_USE_MKL=0 .venv/Scripts/python runs/R-0024/variants.py\` (after R-0022/R-0023 finish; one heavy job at a time).
