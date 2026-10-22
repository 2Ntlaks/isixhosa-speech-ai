<p align="center">
  <img src="docs/readme-hero.png" alt="isiXhosa Speech AI: a speech waveform goes into the R-0012 model and comes out as the isiXhosa sentence 'isizisele uloliwe imoto kunye nezinye izixhobo zothutho'" width="100%">
</p>

<p align="center">
  <img alt="status: paused until 2027" src="https://img.shields.io/badge/status-paused%20until%202027-5d6b7d">
  <img alt="model: whisper-medium" src="https://img.shields.io/badge/model-whisper--medium-142a47">
  <img alt="FLEURS CER: 6.2%" src="https://img.shields.io/badge/FLEURS%20CER-6.2%25-f4715f">
  <img alt="cloud cost: about $32" src="https://img.shields.io/badge/cloud%20cost-~%2432-059669">
  <img alt="licence: MIT" src="https://img.shields.io/badge/licence-MIT-142a47">
  <br>
  <a href="https://ntlakanipho-thetha.static.hf.space/index.html"><img alt="Try the demo" src="https://img.shields.io/badge/%F0%9F%8E%99%EF%B8%8F%20try%20the%20demo-Thetha-f4715f"></a>
  <a href="https://ntlaks.dev/writing/teaching-whisper-isixhosa/"><img alt="Read the story" src="https://img.shields.io/badge/read-the%20story-142a47"></a>
  <a href="https://huggingface.co/Ntlakanipho/whisper-medium-isixhosa"><img alt="Model on Hugging Face" src="https://img.shields.io/badge/%F0%9F%A4%97%20model-whisper--medium--isixhosa-142a47"></a>
</p>

OpenAI's Whisper speaks almost a hundred languages, but **isiXhosa isn't one of them**. Ask stock Whisper to transcribe
isiXhosa and it guesses Swahili, Yoruba or Shona, or switches to a different alphabet altogether. This project fine-tunes Whisper
until it writes isiXhosa properly, one carefully logged experiment at a time, on rented cloud GPUs, for about the price
of a takeaway meal.

It is a learning project by **Ntlakanipho Mgaguli** (Computer Engineering, CPUT). The goal was to understand speech AI
end to end, from raw corpora to a model you can talk to, not just to ship a checkpoint.

> [!TIP]
> **Try it:** speak isiXhosa into **[Thetha](https://ntlakanipho-thetha.static.hf.space/index.html)** on your phone or computer. The small model runs inside your
> browser (about 300 MB, downloaded once), so nothing you record leaves your device.
>
> **Read the story:** [I taught an AI to understand isiXhosa](https://ntlaks.dev/writing/teaching-whisper-isixhosa/), an interactive write-up where you can hear the
> recordings and watch one sentence fix itself stage by stage.
>
> **Use it:** [whisper-medium-isixhosa](https://huggingface.co/Ntlakanipho/whisper-medium-isixhosa) (more accurate) or [whisper-small-isixhosa](https://huggingface.co/Ntlakanipho/whisper-small-isixhosa) (faster) on Hugging Face.

> [!NOTE]
> **Paused for the rest of 2026** ([D-0030](decisions.md)). The models and the demo stay online. Where it stopped:
> - **Medium: [R-0019](runs/R-0019)**, trained with Swivuriso (~146 h of read and unscripted isiXhosa, 407 speakers).
>   On people speaking in their own words its letter errors fell from 10.8 % to 4.1 %; on FLEURS from 8.0 % to 6.2 %.
> - **Small, in the free demo: [R-0027](runs/R-0027)**, with 245 h of Swivuriso including long recordings cut at
>   pauses. Everyday-speech letter errors fell from 11.8 % to 5.1 %.
> - **Mixed isiXhosa–English speech** improved with the new data, without any dedicated mixed-speech training: 38 → 29 % (medium) and
>   42 → 33 % (small) ([R-0030](runs/R-0030)). Still the weakest spot.
> - Ideas for when it restarts: [docs/ideas.png](docs/ideas.png) and the future-work list in [TODO.md](TODO.md).

## Hear the difference

The same FLEURS test sentences, which none of the models saw in training:

| | What each model wrote |
|---|---|
| **Said** | **isizisele uloliwe imoto kunye nezinye izixhobo zothutho** |
| Stock whisper-medium | isisi zisele ulo liwe imo toku nye nizi nyezi kwa wazututu |
| R-0012 (this project) | isizisele uloliwe imoto kunye nezinye izixhobo zothutho ✓ |
| **Said** | **kwimozulu eshushu yase middle east indlu yayingabalulekanga** |
| Stock whisper-medium | kuimuzul esho shiasi mtili isti msu yai inga baluleka |
| R-0012 (this project) | kwimozulu eshushu yase middle east indlu yayingabalulekanga ✓ |
| **Said** | **esi sibini sinokukhetha ukwenza isicwangciso sokwamkelwa komntwana waso** |
| Stock whisper-small | sisi bini suyo kiki kwa kwa kwa kwa kwa kwa kwa kwa … *(stuck in a loop until it ran out of length)* |
| R-0012 (this project) | esi sibini sinokukhetha ukwenza isicwangciso sokwamkelwa komntwana waso ✓ |

<sub>Outputs copied from <code>runs/R-0011/eval_fleurs</code>, <code>runs/R-0006</code> and <code>runs/R-0012/eval_fleurs</code>. Sentences from Google FLEURS (CC BY 4.0).</sub>

## The journey

<p align="center">
  <img src="docs/readme-progress.png" alt="Bar chart of character error rate on unseen FLEURS isiXhosa sentences: stock whisper-small 65.5%, stock whisper-medium 45.9%, small trained on NCHLT 29.8%, small plus FLEURS 10.2%, medium plus FLEURS 8.0%" width="100%">
</p>

| Stage | What happened | Outcome |
|---|---|---|
| **1 · Baseline** | Stock Whisper on 2 770 isiXhosa clips. It guessed 52 different languages and wrote 30 % of its output in non-Latin scripts. | CER 75 % ([R-0001](runs/R-0001)) |
| **2 · First fine-tune** | whisper-small on 51 hours of NCHLT read speech, about $1.85 of GPU. It learned the corpus's short prompts so well that it glued words together on longer sentences. | NCHLT CER 46 → 3 % ([R-0004](runs/R-0004)) |
| **3 · Improve** | Adding 13 hours of varied FLEURS sentences fixed the word-gluing. Moving from small to medium helped on every test set. An 8-bit copy runs on a laptop at the same accuracy. | FLEURS CER 8 % ([R-0012](runs/R-0012), [R-0013](runs/R-0013)) |
| **3b · More data** | Added Swivuriso (South Africa African Next Voices): 146 h of read and unscripted speech from 407 new speakers, with every test and dev sentence kept out. Same model and recipe otherwise. | FLEURS CER 6.2 %, unscripted speech 10.8 → 4.1 % ([R-0019](runs/R-0019)) |
| **3c · Long recordings** | Cut 8 787 long unscripted Swivuriso recordings at pauses into 98.9 h of extra training pieces (`src/swivuriso_long.py`). The small model trained on them halved its everyday-speech errors and became the demo model; the medium gained less, missed its ship rule by 0.02 and stays at R-0019. | small: unscripted CER 11.8 → 5.1 % ([R-0027](runs/R-0027)); medium: tie ([R-0029](runs/R-0029)) |
| **4 · Mixed speech** | Tested on real isiXhosa–English TV dialogue. At first the model heard English words but spelled them the isiXhosa way ("stubborn" came out as "istabhunga"). The Swivuriso data fixed much of that without dedicated mixed-speech training (dedicated training is designed, not run). | CER 38 → 29 % ([R-0014](runs/R-0014), [R-0030](runs/R-0030)) |
| **5 · Ship** | Code made open source; both models published on Hugging Face; a free demo that runs the small model in the visitor's browser, checked to keep its accuracy ([D-0019](decisions.md), [D-0020](decisions.md), [R-0017](runs/R-0017), [R-0028](runs/R-0028)). | [demo](https://ntlakanipho-thetha.static.hf.space/index.html) · [model](https://huggingface.co/Ntlakanipho/whisper-medium-isixhosa) |

## Use the model

```python
from transformers import pipeline

asr = pipeline("automatic-speech-recognition", model="Ntlakanipho/whisper-medium-isixhosa")
print(asr("clip.wav", generate_kwargs={"language": "sw", "task": "transcribe"})["text"])
```

Always pass `language="sw"`: the model borrows Whisper's Swahili tag for isiXhosa, but writes isiXhosa.

## Results

Lower is better. **CER** counts letters wrong and **WER** counts words wrong. isiXhosa words are long, so one wrong
letter fails a whole word; CER is the fairer headline.

| Model | NCHLT test<br><sub>read speech</sub> | FLEURS test<br><sub>unseen sentences</sub> | Soapies test<br><sub>isiXhosa + English TV</sub> |
|---|---|---|---|
| Stock whisper-medium ([R-0011](runs/R-0011)) | 33.7 / 137.2 | 45.9 / 142.3 | – |
| whisper-small, NCHLT ([R-0004](runs/R-0004)) | 2.98 / 16.6 | 29.8 / 94.9 | – |
| whisper-small, NCHLT + FLEURS ([R-0007](runs/R-0007)) | 2.91 / 16.8 | 10.2 / 44.4 | 42.1 / 88.0 |
| whisper-medium, NCHLT + FLEURS ([R-0012](runs/R-0012)) | 2.33 / 12.7 | 8.03 / 37.8 | 38.4 / 79.6 |
| whisper-small, + Swivuriso 245 h ([R-0027](runs/R-0027), the demo) | 3.37 / 21.6 | 8.89 / 38.2 | 32.8 / 71.5 |
| **whisper-medium, + Swivuriso 147 h ([R-0019](runs/R-0019))** | **2.31 / 13.7** | **6.24 / 30.3** | **29.3 / 66.6** |
| whisper-medium, + Swivuriso 245 h ([R-0029](runs/R-0029), not published) | 2.32 / 14.2 | 6.16 / 29.8 | 28.1 / 64.3 |

<sub>Each cell is CER / WER in %. Every run, including the failed ones, is in <a href="results.md">results.md</a>.
On the Swivuriso test (2 145 clips of 1–30 s, 24 speakers of its own), R-0019 scores 4.12 / 19.1 against R-0012's
9.00 / 37.3 (<a href="runs/R-0018">R-0018</a>); R-0027 5.25 / 24.0 against R-0007's 9.88 / 42.5; R-0029 4.14 / 18.1, which
missed R-0019's CER by 0.02 because of one runaway output. Soapies scores come from the 8-bit copies on CPU
(<a href="runs/R-0030">R-0030</a>; R-0029 in <a href="runs/R-0031">R-0031</a>, where R-0019 scored 29.6 / 66.9).</sub>

> [!IMPORTANT]
> **Reading these numbers honestly**
> - **NCHLT flatters the model.** 82 % of its test clips repeat a training sentence. On sentences it never saw,
>   R-0019 scores CER 4.4 / WER 26.6 (R-0012: 5.0 / 28.7).
> - **FLEURS is the fair score**, but not a brand-new dataset: every model since R-0007 trained on FLEURS's training
>   split; only its test sentences are unseen. CER 6 % still means about one word in four has a slip.
> - **The Swivuriso test is home ground** for R-0019 (same recording project and topics as its new training data), and
>   it covers short, fully transcribed clips only.
> - **The model tags isiXhosa as Swahili.** It borrows Whisper's `<|sw|>` token ([D-0007](decisions.md)).

## How it works

<p align="center">
  <img src="docs/readme-pipeline.png" alt="Pipeline: speech corpora are downloaded by a small machine into a private S3 bucket; each run is a folder with job.sh and a git commit, executed on one self-terminating GPU machine; results return to git; the best model becomes an 8-bit copy for the Thetha page on a laptop" width="100%">
</p>

- **Data never touches the laptop.** A small cloud machine downloads each corpus, checks it against the publisher's
  checksum, stores it in a private S3 bucket and switches itself off.
- **Every experiment is a folder.** `runs/R-xxxx/job.sh` runs on one GPU machine, which receives the exact git commit,
  installs pinned packages, trains and scores, uploads, and shuts down under a hard time cap.
- **The training choices**: whole speakers are held out as a dev set, the checkpoint with the lowest dev CER is kept,
  and a run resumes if the machine dies. One light text normalisation is shared by every score, so results stay
  comparable.
- **Everything is written down.** 21 problems ([problems.md](problems.md)), 30 decisions
  ([decisions.md](decisions.md)) and a session-by-session [JOURNAL](JOURNAL.md).

<details>
<summary><b>Run it yourself</b></summary>

<br>

**Thetha, the talk-to-it page (laptop, CPU only).** This needs Python 3.12 and ffmpeg. The models are not in this repo:
copy the `ct2-int8/` folder of each Hugging Face model into `data/models/` as `R-0019-int8` (medium) and
`R-0027-int8` (small).

```powershell
python -m venv .venv
.venv\Scripts\pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\pip install transformers==4.46.3 ctranslate2==4.5.0 soundfile jiwer scipy
$env:CT2_USE_MKL="0"; .venv\Scripts\python src\live.py
```

Open http://127.0.0.1:7860, press record and speak. It only listens on your own computer.

The live server warms only the default model; the first comparison loads its second model on demand.
It processes one 30-second chunk at a time to bound feature and model working memory, and reuses compatible
features when comparing models. It still decodes the complete uploaded recording into RAM.
`--chunk-batch-size 2` trades more RAM for larger inference batches. `--threads 4` sets CPU parallelism explicitly;
the default remains PyTorch's thread count. Beam 5, the language tag and token limits stay unchanged.
Measurements and limitations: [R-0025](runs/R-0025/run.md).

**Cloud runs.** These need the AWS CLI logged in, an S3 bucket and an EC2 instance role.

```bash
cloud/fetch_data.sh --job fetch-1 --datasets nchlt,fleurs      # once: datasets into S3
cloud/run_job.sh --run R-0012 --type g6e.xlarge --market ondemand --max-hours 6
cloud/wait.sh R-0012 && cloud/collect.sh R-0012                 # follow it, then pull results into runs/
```

</details>

<details>
<summary><b>What's where</b></summary>

<br>

| Path | Contents |
|---|---|
| `src/` | Data loaders (NCHLT, FLEURS, Soapies), training, evaluation, scoring, the Thetha live page |
| `cloud/` | Launch, follow and collect cloud jobs; the dataset downloader; machine boot scripts |
| `runs/` | One folder per experiment: command, config, logs, metrics, sample outputs, loss curves |
| `docs/` | Hand-drawn explainer sheets and the scripts that draw them |
| `evidence/` | A results page per stage, written for a non-technical reader |
| `SPEC.html` | The original project plan |
| `JOURNAL.md` · `results.md` · `problems.md` · `decisions.md` | The project's record, append-only |
| `AGENTS.md` | Working rules for the coding agents that built this |

</details>

## Data and credits

| Dataset | Used for | Licence |
|---|---|---|
| [NCHLT isiXhosa Speech Corpus](https://hdl.handle.net/20.500.12185/279), CSIR Meraka Institute and North-West University, via SADiLaR | training and test, ~56 h | CC BY 3.0 |
| [Google FLEURS](https://huggingface.co/datasets/google/fleurs) `xh_za` | training and test, ~13 h | CC BY 4.0 |
| [Swivuriso: South Africa African Next Voices](https://huggingface.co/datasets/dsfsi-anv/za-african-next-voices), isiXhosa, by the South Africa NextVoices team (DSFSI, University of Pretoria) | training (146 h) and test, from R-0019 | CC BY 4.0, speech recognition only (no TTS or voice cloning); gated, never re-hosted here |
| [NCHLT English Speech Corpus](https://hdl.handle.net/20.500.12185/274), via SADiLaR | stage 4 training (prepared, never run) | CC BY 3.0 |
| [Multilingual code-switched soap opera speech](https://hdl.handle.net/20.500.12185/545), van der Westhuizen & Niesler, Stellenbosch University (LREC 2018) | **testing only**, never trained on ([D-0016](decisions.md)) | research only |

No audio, corpus files or model weights are stored in this repository. Built on
[OpenAI Whisper](https://github.com/openai/whisper) via Hugging Face Transformers, and
[CTranslate2](https://github.com/OpenNMT/CTranslate2).

**Limitations.** Most training speech is read aloud or short (clips of 30 s or less), so fast, run-together
conversation and noise are still weak spots. Since R-0019 the model writes English words in English, but sometimes
guesses an English word too eagerly (the name "Thetha" came out as "tether" in a live test).
The code-switched test set has only 5 speakers. The model writes no punctuation or capitals, and writes prefix +
loanword with a space (`e afrika`, not `e-Afrika`).

## Licence

The code and project documents are under the [MIT License](LICENSE). This does not cover the datasets or the dataset
transcripts quoted in run outputs (`runs/*/predictions.jsonl`, `samples.md`), which keep their own licences (above).
