# Decisions

Real choices, made by the founder (or proposed by an agent and approved). Append-only.

Format:

    ## D-0001 · YYYY-MM-DD · <the question>
    - Options: <A / B / C, one line each>
    - Recommendation: <agent's pick and why>
    - Decision: <what the founder chose>
    - Why: <his reason>

## D-0001 · 2026-10-16 · Which AI project should the AWS credits go to?
- Options: AI study partner for Tutoring / load-shedding energy monitor / render farm as a service /
  GPT from scratch / Gaussian-splat CPUT / fine-tune Whisper for isiXhosa
- Recommendation: GPT from scratch, then Whisper isiXhosa (learning path)
- Decision: fine-tune Whisper for isiXhosa
- Why: founder's goal is "learn something hard" in AI/ML; this one is interesting to him.

## D-0002 · 2026-10-16 · Who writes the code?
- Decision: agents (founder's Claude Code sessions) write, test, validate and operate everything, including server access.
  The founder is architect and decision-maker and must understand the system.
- Why: founder's explicit choice; understanding over typing.

## D-0003 · 2026-10-16 · Does the founder speak isiXhosa? (SPEC §10, question 1)
- Answer: yes.
- Consequences: stage 4 uses the founder's own mixed isiXhosa/English recordings; the founder checks
  transcripts and judges model errors by ear (e.g. "wrong click", "wrong word boundary", "dialect spelling").
  Agents still never invent isiXhosa text; the founder is the source for any text not in the datasets.

## D-0004 · 2026-10-16 · Where do the datasets live?
- Options: A) download to the laptop / B) download in the cloud straight into the private S3 bucket
- Recommendation: B. Laptop C: has 70 GB free (86 % used); datasets are ~8 GB of archives. Training nodes read
  S3 in the same region for free. The laptop only pulls the ~100 stage-1 test clips plus whisper-small (~1 GB).
- Decision: B (founder agreed 2026-10-16).
- Why: save local disk. Drawing: docs/data-flow.png.
- Note: S3 bucket mgaguli-studio-render-<acct> (us-east-1), prefix datasets/ (the 30-day auto-delete only covers jobs/).

## D-0005 · 2026-10-16 · Accept the NCHLT isiXhosa Speech Corpus licence (CC BY 3.0)
- Finding: SADiLaR serves the corpus (nchlt.speech.corpus.xho.zip, 5.01 GB, MD5 0e8918da0e1ac9acb3a300c7198c33dd,
  handle 20.500.12185/279) without a login, so no SADiLaR account is needed; the cloud downloader fetches it directly.
- Decision: the founder accepts the CC BY 3.0 terms: credit CSIR Meraka Institute and North-West University (via SADiLaR)
  in the model card and write-up, no implied endorsement, never re-upload the raw audio.
- Why: required before downloading; founder's own acceptance per AGENTS.md.

## D-0006 · 2026-10-16 · Where and how to run the stage 1 baseline
- Options: A) laptop, 100 test clips (original plan) / B) cloud GPU, full NCHLT test set (2 770 clips)
- Recommendation: B. Data is already in S3 (D-0004), the full test set gives a more trustworthy number than 100 clips,
  and it rehearses the GPU node setup stage 2 needs. Cost well under $1. Language: let Whisper auto-detect per clip
  (shows what happens today, and records which language it mistakes isiXhosa for).
- Decision: B, auto-detect. Founder: "you can do it in the cloud and report results here... I trust you".
- Why: keep the laptop free; founder will read results on a results page.

## D-0007 · 2026-10-17 · Language tag for isiXhosa in the first fine-tune
- Options: A) reuse Swahili's tag (<|sw|>) / B) add a new <|xh|> token (resize embeddings, new token starts untrained)
- Recommendation: A. Simple, common practice; in R-0001 Whisper's own top guess was Swahili (876 of 2770 clips)
  and those clips were closest (CER 40.3 %). B is a clean stage 3 experiment.
- Decision: A, borrow Swahili's tag.
- Why: founder chose the recommended option. The model card must say the model emits <|sw|> for isiXhosa.

## D-0008 · 2026-10-17 · Spot or on-demand GPU for the first fine-tune
- Options: A) spot first, on-demand fallback (~$1-3) / B) on-demand only (~$0.80/h, ~$2-3)
- Recommendation: A (cheaper; checkpoints every 500 steps make interruptions survivable).
- Decision: B, on-demand only.
- Why: founder prefers never being interrupted for a few dollars more (and spot had no capacity on 2026-10-16, P-0003).
  Checkpoints still go to S3 every 500 steps.

Note 2026-10-17 (finding, not a decision): 1 444 of the 2 066 distinct NCHLT test sentences also occur in the training
split (read by other speakers). From R-0002 on, every evaluation also reports WER/CER on the test clips whose
sentence never occurs in training ("unseen text"), so memorised prompts can't inflate the headline.
