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

## D-0009 · 2026-10-17 · Stage 3, experiment 1: add FLEURS (R-0005, R-0006, R-0007)
- Options: next stage 3 step: A) add FLEURS train data / B) bigger model (whisper-medium) / C) real <|xh|> tag /
  D) augmentation / E) compare with Meta MMS
- Recommendation: A first. R-0004 plateaued from step 3000 and is weak on unseen sentences (6.2 % vs 2.2 % CER);
  varied data targets exactly that. FLEURS test (350 sentences, none in any training data) also becomes a second,
  harder exam. Same recipe as R-0004, one change. ~2.7 h on one on-demand node, about $2.20.
- Decision: A. Founder: "yes do what you have to do", and asked for a reviewer sub-agent to check the code before launch.
- Why: founder agreed with the recommendation; independent review before paid compute.

## D-0010 · 2026-10-17 · How FLEURS text is written for training (agent default, founder may override)
- Finding (reviewer agent): FLEURS's "normalised" transcripts keep hyphens after prefixes before loanwords, names and
  numbers (i-australia, kwi-intanethi, ka-2009; 2 901 hyphens in train), digits and some punctuation. NCHLT text has none.
- Options: A) train on the exact scoring form: hyphen -> space, punctuation removed (scoring.normalise) / B) join the
  hyphenated parts (i-australia -> iaustralia) / C) keep hyphens as written.
- Choice: A. Training targets then match exactly what is scored on both test sets; such words are rare in NCHLT
  (48 joined-form and 300 split-form occurrences across NCHLT train+test), so NCHLT comparability is barely affected.
- Open for the founder: standard isiXhosa orthography writes the hyphen (e-Afrika). If the shipped model should write
  hyphens, that is a later change to both training text and scoring, as its own experiment.

## D-0011 · 2026-10-17 · Stage 3, experiment 2: whisper-medium
- Options: A) whisper-medium on NCHLT + FLEURS (one change vs R-0007: model size) / B) move on to stage 4 or 5 with R-0007
- Recommendation: A, then stage 4. Larger models usually give the biggest single gain; English words inside isiXhosa are
  the main remaining weakness, which stage 4 targets.
- Decision: A. Founder: "yes go with whisper-medium".
- Plan: smoke test R-0008 (~$0.40) to measure memory and speed; the real full-run time and cost go to the founder
  before it starts. Same data, steps (4000 x 32 clips), learning rate (1e-5) and checkpoint rule as R-0007. FLEURS dev
  is added as an information-only second dev check (selection stays on NCHLT dev, so it is not a second change).

## D-0012 · 2026-10-17 · How to train whisper-medium
- Finding (R-0008): on the 24 GB L4, medium fits only with gradient checkpointing, ~9 s/step: ~10 h, ~$8.50, over the 6 h cap.
- Options: A) NVIDIA L40S 48 GB (g6e.xlarge, $1.861/h): no checkpointing, est. ~3x faster, ~3 h, ~$6, after a ~$0.50 smoke
  test / B) L4 overnight, ~10 h, ~$8.50, cap raised to 11 h / C) skip medium, go to stage 4 or 5 with R-0007.
- Recommendation: A. Decision: A (founder).
- Note: the mgaguli-gpu-monthly brake ($20, EC2 compute before credits) showed $7.61 on 2026-10-17 with billing lag;
  after this experiment the month will be near $16-18. Further GPU work this month may need the founder to raise it.

## D-0013 · 2026-10-17 · Run the full whisper-medium experiment (R-0011, R-0012)
- Plan put to the founder with the measured R-0010 numbers: L40S, batch 8 x 4, ~2.7 s/step, ~3.7 h incl. stock-medium
  baselines (R-0011) and both test sets, about $7 (6 h cap, worst case ~$11), 200 GB disk.
- Options: A) run it now / B) keep October's GPU allowance spare and move to stage 4 or 5 with R-0007.
- Recommendation: A. Decision: A. Founder: "tell me when it's done".
- Budget consequence (told to the founder before approval): mgaguli-gpu-monthly counted $7.61 (lagged) + ~$5 of today's
  runs not yet counted + ~$7 ≈ $19-20 for October, at the $20 brake. The brake blocks new launches, not a running job;
  further October GPU runs need the founder to raise it. Project total after this run ≈ $12.70 of the $15-30 budget.

## D-0014 · 2026-10-17 · Where the "talk to the model" API runs
- Founder wants to speak and see the model transcribe live, and asked for an API.
- Options: A) on the laptop: local API + recording page (src/live.py), CPU, free, private / B) Hugging Face Space: from any
  device incl. phone, free but slow on the free CPU tier, needs the founder's HF account / C) AWS always-on GPU API:
  fast, ~$0.80/h while on, breaks the $20 monthly brake; services beyond EC2/S3 need a credits check.
- Recommendation: A now, B later (same code, and it is the stage 5 demo). Decision: "Laptop now, HF later" (founder).
- Notes: the server listens on 127.0.0.1 only. Recordings and the founder's corrections are kept (if the page's "keep"
  box is ticked) in data/my_voice/live/ (gitignored, never uploaded); corrections are the founder's own transcripts,
  usable as stage 4 test material. Local disk: ~4 GB for the two models in data/models/ plus ~1 GB for .venv.

## D-0015 · 2026-10-17 · isiXhosa -> English translation: train Whisper to do it, later
- Finding: R-0012 ignores Whisper's <|translate|> task and still writes isiXhosa (checked on 3 NCHLT clips); fine-tuning
  only ever showed it the transcribe task.
- Options: A) two steps on the laptop: transcript -> Meta NLLB-200 text translation (non-commercial licence) /
  A2) same with Helsinki opus-mt-xh-en (CC BY 4.0, weaker) / B) fine-tune Whisper itself for speech -> English
  (translate task) / C) Claude API as translator (text leaves the laptop; credits check).
- Recommendation: A now, B later. Decision: B, later. Founder: "we will train it later to do that".
- Plan notes for B: FLEURS reads the same FLoRes sentences in every language, so xh_za audio pairs with the official
  en_us text by sentence id (~3.4k training clips, 13 h): training data and an honest test (BLEU/chrF on FLEURS test).
  Train translate and transcribe together so transcription doesn't get worse; one change per run; GPU run ~$4.
  Not before stage 4 has started.

## D-0016 · 2026-10-19 · Stage 4 without the founder recording: which data, and how Soapies may be used
- Founder: too busy to record ~50 test clips plus training clips; this is a prototype to see if delegation works. "find
  a way for now"; if it shows promise he will record a few himself later.
- Finding: two SADiLaR datasets download without a login (checked 2026-10-19 via the repository API):
  1) Corpus of multilingual code-switched soap opera speech ("Soapies", Stellenbosch University, van der Westhuizen &
     Niesler, handle 20.500.12185/545): English-isiXhosa balanced set 3.14 h (balanced_engxho.zip, 338 MB), real
     code-switched speech from Generations and Rhythm City, verbatim XML transcripts, official dev/test utterance ids.
     Licence: "Research only"; the audio is cut from broadcast TV shows.
  2) NCHLT English Speech Corpus (handle 20.500.12185/274): ~56 h South African English read speech, CC BY 3.0.
- Options for Soapies: A) test (and dev) only; any published model is trained only on openly licensed data (NCHLT,
  FLEURS, NCHLT English, and clips stitched from those) / B) also train on the Soapies train part, model kept private
  forever / both.
- Recommendation: A. Decision: **A** (founder, 2026-10-19).
- Consequences: Soapies lives only in the private S3 bucket (datasets/soapies_engxho/) and on the laptop for scoring;
  never re-hosted, never in a Hugging Face repo or Space, never used for training. Cite van der Westhuizen & Niesler
  (LREC 2018) wherever a Soapies score appears. NCHLT English: credit CSIR Meraka / North-West University like NCHLT.
  The founder's own recordings stay optional, as a final check later.

## D-0017 · 2026-10-19 · Stage 4 training recipe (agent default under D-0016, founder may override)
- Finding (R-0014): on real code-switched speech R-0012 gets CER 38.4 / WER 79.6; only 32 % of English words and 15 %
  of isiXhosa words come out right. It writes English words with isiXhosa spelling; fast acted TV speech also hurts.
- Choice: two runs on one node, continuing from R-0012 (cheaper than retraining; stage 4 specialises the stage 3 model),
  2000 steps, lr 5e-6: R-0015 adds 10 h NCHLT English (<|en|> tag); R-0016 adds 8000 stitched isiXhosa+English clips
  on top (one change). Checkpoint chosen on Soapies dev (dev use, allowed by D-0016). Scored on Soapies test (headline),
  NCHLT and FLEURS test (must not get much worse).
- Why two runs: the founder wants to learn what works; the pair shows separately what English alone and stitching add.
- Spend: ~$5-6, after the 1 November brake reset. The founder delegated the next steps ("move on to next thing, I
  trust your judgment", 2026-10-19) but has not yet seen this recipe; the launch waits for his OK on the spend.
