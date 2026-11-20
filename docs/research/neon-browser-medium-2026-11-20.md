# Research Report: Running `whisper-medium-isixhosa` (R-0035) in the Free Browser Demo

- **Date:** 2026-11-20
- **Author:** Neon (research sub-agent)
- **For:** Founder (decision-maker) and Lead (Claude verifier)
- **Question:** Can our best model (`whisper-medium-isixhosa`, run R-0035) run inside the free static Hugging Face Space (`https://ntlakanipho-thetha.static.hf.space/index.html`), and what is the best route? Compare (1) squeezed medium in the browser, (2) distilling/teaching small from medium, (3) both (progressive hybrid), plus any first-principles alternative.
- **Constraints honored:** Zero cloud spend; zero repo edits outside this file; every external URL directly read and verified HTTP 200 on 2026-11-20; source facts strictly separated from Neon's inferences; full Claims Ledger at the end.

---

## Plain-Language Summary (for the Founder)

**Short answer: Yes — our best model (R-0035 medium) can run inside a modern laptop browser for free, using WebGPU and 4-bit compression (~522 MB one-time download instead of 3.06 GB). However, it is too heavy and fragile to force on every phone or older browser. The best route is a Hybrid demo (Route 3): keep the light Small model as the fast default that works on every phone, and add an optional "High Accuracy (Medium)" switch for capable devices.**

Here is why, in plain terms:

1. **Squeezing Medium into the browser (Route 1) works best via `transformers.js` v4 + WebGPU — not CPU-only WASM or `whisper.cpp`.**
   - Our demo currently uses an older `transformers.js` (v3.0.2, CPU-only WASM). The latest `transformers.js` (v4.3.2, October 2026) has a brand-new C++ WebGPU engine and supports Chrome, Edge, Firefox (Windows & Apple Silicon Macs), and Safari 26 (macOS & iOS).
   - Shrinking R-0035 medium to 4-bit (`q4f16`) brings the one-time download to **~522 MB** (compared to ~295 MB for the current Small demo). If Whisper's audio encoder turns out to be too sensitive to 4-bit and needs 16-bit (`fp16` encoder + `q4f16` decoder, which Hugging Face's own Whisper demos use), the download jumps to **~956 MB**.
   - **Why it cannot replace Small for everyone:** ~520 MB–960 MB is expensive on South African mobile data; loading it briefly uses ~1.5–2.5 GB of RAM/GPU memory, which causes iPhones and mid-range Android phones to silently crash the browser tab; ~15% of browsers globally still lack WebGPU; and Safari erases cached web files if you do not revisit the site for **7 days**.
   - **Important catch we verified in the code:** `transformers.js` v4.3.2 still does **not** support beam search (so Medium runs greedy, which costs only +0.14 to +0.35 CER on R-0035 — still vastly better than Small), and it has no built-in loop guard, **but** we can add our exact gzip loop guard in ~20 lines of JavaScript plus a 0.64 MB voice detector (Silero VAD) so silence stops producing invented words.

2. **Teaching Small from Medium (Route 2: distillation) will not close the gap on its own — and there is a cheaper step first.**
   - Before spending money on distillation, notice a key fact from our own run logs: our current Small model (`R-0027`, Swivuriso CER 5.25, FLEURS 8.89) was trained with our **old, under-trained recipe** (4,000 steps, no SpecAugment, NCHLT-only checkpoint choice, 96-token dev cap). Fixing that exact recipe on Medium (`R-0029` → `R-0035`) cut error noticeably. Simply retraining Small with R-0035's fixed recipe costs **~$4.50–$5.20** and upgrades every phone user at the same ~295 MB size.
   - Published research on distilling Whisper into Small on the same labelled low-resource audio shows only a **tiny extra gain (~0.2–0.6 WER)** over standard fine-tuning. The real gap between Small and Medium (~6–8 WER on matched recipes) comes from Small's smaller "ears" (12 encoder layers vs 24). Pseudo-labelling works best with thousands of hours of extra unlabelled speech, which we do not have for isiXhosa.

3. **Best plan: Hybrid (Route 3), starting with a $0 laptop test before spending a cent.**
   - **Step A ($0, on this laptop):** Convert our existing `R-0035` weights to 4-bit and 16-bit ONNX, measure the exact isiXhosa accuracy loss on 100 FLEURS + 200 NCHLT clips, and test real Chrome/Edge WebGPU speed and memory on your Radeon 780M laptop.
   - **Step B (if Step A passes):** Upgrade the free Hugging Face Space to `transformers.js` v4.3.2 with Small as the safe default + an opt-in **"High Accuracy (Medium · R-0035)"** button that only appears on WebGPU-capable devices and shows the exact MB download size before downloading.
   - **Step C (optional later, ~$5 after the monthly GPU brake resets):** Retrain Small with R-0035's fixed recipe so mobile and non-WebGPU users get a much better default too. Only after that would we even consider an experimental "pruned Medium" (24 encoder layers + 4 decoder layers, ~250 MB in 4-bit, ~$6 GPU) — an intriguing research bet, but unproven at 310 h of isiXhosa.

---

## 1. Verified Project Context & Ground Truth

All numbers below were verified directly against repository files and `data/models/R-0035/model.safetensors` on 2026-11-20.

### 1.1 Current Models & Measured Accuracy

| Property | `whisper-medium-isixhosa` (R-0035) | `whisper-small-isixhosa` (R-0027) | Source |
|---|---|---|---|
| Base architecture | `openai/whisper-medium` (24 enc / 24 dec, `d_model=1024`, 16 heads, vocab 51,865, 80 mel bins) | `openai/whisper-small` (12 enc / 12 dec, `d_model=768`, 12 heads) | `data/models/R-0035/config.json`; Whisper paper / `arXiv:2311.00430` Table 1 |
| Parameter count | **763,857,920** tied in `model.safetensors` (commonly cited as 769M); **816,967,680** if `proj_out` is untied from `embed_tokens` | ~244M tied (~284M untied) | Direct safetensors header inspection (R-0035); `arXiv:2311.00430` Table 1 |
| Exact R-0035 parameter split | Encoder: **307,216,384** (303.53M 2D linear); Decoder (excl. embeddings): **403,531,776** (403.11M 2D linear); `embed_tokens` (`51865×1024`): **53,109,760** | — | Direct header inspection of `data/models/R-0035/model.safetensors` |
| Weight sizes on disk / HF | fp32 `model.safetensors`: **3,055.54 MB** (3.06 GB); `ct2-int8/model.bin`: **774.73 MB** | `ct2-int8/`: **240 MB**; browser ONNX q8: **98.19 MB** enc + **196.58 MB** dec = **294.77 MB** | Local `data/models/R-0035*`; `runs/R-0028/run.md` L7, L25; HF API |
| Training data & recipe | 309.7 h (98,663 clips), **fixed recipe**: 9,000 steps (~2.9 epochs), SpecAugment, Swivuriso+FLEURS dev selection (kept step 8,000), 225-token dev cap | **Same 309.7 h**, **old recipe**: 4,000 steps (~1.3 epochs), no SpecAugment, NCHLT-only dev selection (kept step 3,500), 96-token dev cap | `runs/R-0035/run.md` L11–31; `runs/R-0027/run.md` L16–18, L47; `docs/research/lead-verification-2026-11-19.md` L8, L22 |
| Language & prompt setup | `language: "sw"` (`<\|sw\|>` id 50318), `task: "transcribe"` (50359), `return_timestamps: false` (`<\|notimestamps\|>` 50363), `forced_decoder_ids: null`, custom `suppress_tokens` & `begin_suppress_tokens` | Same `<\|sw\|>` / transcribe / no-timestamps setup | `data/models/R-0035/generation_config.json`; `decisions.md` D-0007 |
| Swivuriso `dev_test` (2,145 clips) | Beam 5 + guard (CT2 fp16 GPU): **15.04 WER / 3.24 CER** (unscripted 13.4 / 2.8); Greedy (`transformers` fp16): **15.51 / 3.38** | Greedy (`transformers` fp16): **24.03 / 5.25** (unscripted 23.0 / 5.1) | `runs/R-0035/run.md` L123, L129, L138; `runs/R-0027/run.md` L51–52 |
| FLEURS `xh_za` test (1,034 clips) | Beam 5 + guard: **26.06 / 5.21**; Greedy: **26.64 / 5.56** | Greedy: **38.18 / 8.89** | `runs/R-0035/run.md` L124, L138; `runs/R-0027/run.md` L53 |
| NCHLT test (2,770 clips) | Beam 5 + guard: **11.11 / 1.92** (unseen 24.4 / 4.1); Greedy: **11.45 / 1.99** (unseen 25.5 / 4.3) | Greedy: **21.56 / 3.37** (unseen 33.3 / 5.3) | `runs/R-0035/run.md` L125, L131, L138; `release/model-card-medium.md` L88; `runs/R-0027/run.md` L54–55 |
| Soapies code-switched test (391 clips) | Beam 5 + guard: **60.84 / 25.98** | Greedy CPU int8 (R-0030): **71.48 / 32.80** | `runs/R-0035/run.md` L126; `results.md` L44 |
| Quantisation cost measured so far | CT2 int8 on 100 FLEURS clips (R-0036/R-0037): **+0.19 CER** (`ct2 4.5.0`: 6.16 vs 5.97 GPU fp16 / 5.94 CPU fp32) to **+0.35 CER** (`ct2 4.8.1`: 6.32) | ONNX q8 on 200 NCHLT unseen clips (R-0028): **+0.16 CER** (6.07 vs 5.91 GPU fp16; 175/200 identical) | `runs/R-0037/run.md` L20–33; `runs/R-0028/run.md` L13 |
| Speed measured on founder's laptop | CPU `src/live.py` (CT2 int8, beam 5): 12.8 s live clip in **7.1 s** (D-0033); 100 FLEURS clips (1,281 s audio, 8 threads) in **772 s** (~7.72 s/clip, RTF ~0.60, R-0037) | Python ONNX q8 CPU: **2.99 s/clip** (NCHLT); Chrome WASM (16 threads, COOP/COEP): **6.9–7.3 s** (3 s NCHLT clip), **9.0–9.4 s** (14.2 s founder clip); 1-thread WASM (R-0017): **18.7 s** | `decisions.md` D-0033; `runs/R-0037/run.md` L23; `runs/R-0028/run.md` L14, L21–22, L30–31; `runs/R-0017/run.md` L24–25 |

### 1.2 Current Browser Demo Architecture & Constraints
- **Hosting:** Free Hugging Face Static Space (`sdk: static`, $0; Gradio/Docker free CPU Spaces require PRO at $9/month, `problems.md` P-0014). Sets `COOP: same-origin`, `COEP: require-corp`, `CORP: cross-origin` so `SharedArrayBuffer` multi-threaded WASM works (`release/web/README.md` L12–15).
- **Runtime:** `@huggingface/transformers@3.0.2` self-hosted from the Space (`release/publish_web.py` L22–23 extracts `transformers.min.js` and `ort-wasm-simd-threaded.jsep.wasm`), running inside a Web Worker (`release/web/worker.js`) with `device: "wasm"`, `dtype: { encoder_model: "q8", decoder_model_merged: "q8" }`, fixed 30 s chunks, `language: "sw"`, `task: "transcribe"`, `max_new_tokens: 225`, greedy decoding, no VAD, no loop guard.
- **Caching:** Uses Cache Storage (`caches.open("transformers-cache")`, `release/web/index.html` L121) and waits for a user tap on first visit before downloading (~300 MB).
- **Hardware on founder's laptop** (verified locally): AMD Ryzen 7 PRO 250 (8 cores / 16 logical threads) with **AMD Radeon 780M integrated GPU**, 15.3 GB RAM (~4.3 GB free during active desktop use — see P-0011 and P-0013), Windows, Chrome and Edge installed, global Python 3.12.10 (`torch 2.12.1+cpu`, `transformers 4.46.3`, `ctranslate2 4.5.0`, `onnxruntime 1.27.0`), Node.js installed.
- **Important recipe confound (Inference from repo facts):** `R-0027` (small) and `R-0029` (medium) used the **exact same data (309.7 h) and exact same old 4,000-step recipe**: small scored Swivuriso 24.03 / 5.25 and FLEURS 38.18 / 8.89, while medium scored Swivuriso 18.12 / 4.14 (3.90 without one runaway) and FLEURS 29.80 / 6.16 (`results.md` L40–46). Earlier, on identical 64.2 h data (`R-0007` vs `R-0012`), small scored FLEURS 44.38 / 10.16 vs medium 37.83 / 8.03 (`results.md` L15, L22). Thus, **~6–8 WER / ~1.3–2.7 CER** of the current `R-0027` vs `R-0035` gap is pure model-size capacity, while an additional **~2.6–3.2 WER / ~0.6–0.8 CER** (the `R-0029` → `R-0035` greedy gain) is simply the recipe fix that has not been applied to `whisper-small` yet.

---

## 2. Route 1: Squeezed `whisper-medium` in the Browser

### 2.1 Candidate Browser Runtimes Compared

| Route (version verified 2026-11-20) | First-visit download (Medium) | Hardware accel | Laptop speed (12–15 s clip) | Phone viability | Handles our `<\|sw\|>` + `generation_config` + loop guard? | Maintenance / complexity |
|---|---|---|---|---|---|---|
| **1A. `transformers.js` v4.3.2 (`onnxruntime-web` 1.31.x) — WebGPU** | **~522 MB** (`q4f16`); **~684 MB** (`q4`); **~956 MB** (`fp16` enc + `q4f16` dec) + ~29 MB WASM glue (uncompressed) | **WebGPU** (rewritten C++ runtime, KV cache kept in `gpu-buffer`) | **UNVERIFIED** (Inference: ~1–5 s warm on iGPU like Radeon 780M / M-series after one-time shader warm-up) | **Risky/poor as default:** high OOM/Jetsam risk on 4–6 GB phones + heavy mobile data + Safari 7-day cache wipe | **Yes**, with 2 caveats: (1) greedy only (no `num_beams: 5` in v4.3.2), (2) must export without `cache_position` (P-0015 still open) & write ~20-line JS gzip loop guard | **Low** — direct upgrade of current `worker.js` |
| **1B. `transformers.js` v4.3.2 — WASM (CPU)** | **~776–829 MB** (`q8`, tied vs untied); **~684 MB** (`q4`) | Multi-threaded WASM SIMD (requires COOP/COEP, already set) | **UNVERIFIED** (Inference: **~20–30 s** on 16-thread laptop, ~60+ s 1-thread) | **Not viable** (extreme latency + mobile WASM heap / Jetsam crash risk) | Same as 1A | Low (same worker, `device: "wasm"`) |
| **1C. `whisper.cpp` v1.9.5 (`examples/whisper.wasm`)** | **539 MB** (`q5_0`); **823 MB** (`q8_0`); **1,534 MB** (`fp16`) | **WASM CPU SIMD only** in `whisper.wasm` (`ggml-webgpu` exists in vendored `ggml`, not wired into `whisper.wasm`) | **Official README:** *"models up to size `small` inclusive. Beyond that, the memory requirements and performance are unsatisfactory."* | **Not viable** (`MAXIMUM_MEMORY=2000MB`, MEMFS double-buffering peak) | **Partial / high effort:** `convert-h5-to-ggml.py` ignores `generation_config.json`; stock JS binding hardcodes greedy + timestamps; custom C++/Emscripten fork needed for beam 5, `no_timestamps`, `entropy_thold` | **High** — custom Emscripten C++ build + custom HF→GGML verification |
| **1D. `candle` WASM / `sherpa-onnx` WASM / raw `onnxruntime-web`** | Candle: ~800 MB+ (`q8`); `sherpa-onnx`: CPU WASM only; raw ORT Web: same as 1A | Candle & `sherpa-onnx` Whisper WASM are CPU-only; raw ORT Web has WebGPU | Candle/sherpa too slow for medium; raw ORT Web = same speed as 1A | Not viable (CPU WASM) or same limits as 1A (raw ORT Web) | Raw ORT Web would require rewriting Whisper mel/BPE/decoder loop from scratch just to add beam search | **High** — no net advantage over `transformers.js` v4 |

---

### 2.2 Deep Dive on Each Criterion for Route 1

#### A. Realistic First-Visit Download Size (Source Facts)
Exact file sizes retrieved directly from Hugging Face Hub APIs on 2026-11-20 for `onnx-community/whisper-medium-ONNX`, `Xenova/whisper-medium`, `ggerganov/whisper.cpp`, and `Ntlakanipho/whisper-small-isixhosa`:

| Precision / format | Encoder file | Merged Decoder file | Model total (+ ~5 MB tokenizer/config) | Notes (verified from HF Hub & source) |
|---|---|---|---|---|
| **Current demo:** R-0027 `small` ONNX `q8` (untied) | 98.19 MB | 196.58 MB | **294.77 MB** (~300 MB) | Live today (`Ntlakanipho/whisper-small-isixhosa/onnx`). Note `onnx-community/whisper-small` tied `q8` is 92.33 + 156.75 = 249.08 MB. |
| **Medium ONNX `q4f16`** | 180.63 MB | 336.28 MB | **516.91 MB (~522 MB)** | Smallest ONNX option (`onnx-community/whisper-medium-ONNX`). Requires WebGPU `shader-f16`. |
| **Medium ONNX `q4`** | 209.95 MB | 469.35 MB | **679.31 MB (~684 MB)** | No `shader-f16` needed. +162 MB vs `q4f16` mainly because `embed_tokens` (53.1M params) stays fp32 (212 MB) instead of fp16 (106 MB). |
| **Medium ONNX `q8` (tied vs untied)** | 313.15–313.47 MB | 462.66 MB (tied, `Xenova`) / ~516 MB (untied, `export_onnx.py`) / 672.56 MB (naive `onnx-community` bug) | **~776–829 MB** (or 986 MB naive) | `onnx-community/whisper-medium-ONNX` hit the same P-0015 tied-embedding `Transpose` skip (leaving 212 MB fp32 in decoder `q8`). Untying as in `src/export_onnx.py` keeps both `embed_tokens` and `embed_tokens_T` in int8 (~516 MB decoder). |
| **Medium ONNX `fp16` enc + `q4f16` dec** | 614.72 MB | 336.28 MB | **951.00 MB (~956 MB)** | Follows Hugging Face's high-precision-encoder pattern (`webml-community/whisper-large-v3-turbo-webgpu`). |
| **Medium ONNX `fp16` enc + `q4` dec** | 614.72 MB | 469.35 MB | **1,084.07 MB (~1.09 GB)** | High-precision encoder without fp16 decoder. |
| **Medium `whisper.cpp` GGML `q5_0` / `q8_0`** | Single `.bin` | Single `.bin` | **539.21 MB** (`q5_0`) / **823.37 MB** (`q8_0`) | `ggerganov/whisper.cpp` (fp16 is 1,533.76 MB). |

**Runtime bundle overhead (`transformers.js` v4.3.2 packaging change):**
- In `@huggingface/transformers@4.3.2` (published 2026-10-27 on npm, GitHub release 2026-10-28), `ort-wasm-simd-threaded.jsep.wasm` is **no longer inside the `@huggingface/transformers` package** (verified via jsDelivr package listing: only `dist/transformers.web.min.js`, 0.46 MB, and `.mjs` wrappers are bundled).
- Instead, `packages/transformers/src/backends/onnx.js` L354–364 loads the C++ WebGPU/WASM binary from `onnxruntime-web@1.31.0-dev.20260914-8d85527a0`: **`ort-wasm-simd-threaded.asyncify.wasm`** (**28.75 MB** uncompressed in `onnxruntime-web@1.31.1`) plus its `.mjs` loader (0.05 MB), falling back to non-asyncify `ort-wasm-simd-threaded.wasm` (14.85 MB) on Safari < 26 without WebGPU. To keep our COOP/COEP self-hosting working, `release/publish_web.py` must fetch these files from the pinned `onnxruntime-web` npm tarball alongside `@huggingface/transformers@4.3.2`.
- **South Africa context (Inference):** On mobile data (prepaid/capped cellular), a 522 MB–956 MB first-visit download is a major barrier compared to ~295 MB (and catastrophic if Safari evicts it after 7 days; see §2.2.D).

#### B. Speed: Laptop (WebGPU vs WASM) and Mid-Range Phone
- **Verified facts:**
  - `transformers.js` v4 (announced Feb 9, 2026; 4.0.0 tagged Mar 30, 2026; 4.3.2 Oct 28, 2026) replaced its JS WebGPU glue with a C++ WebGPU Runtime built with ONNX Runtime (`huggingface.co/blog/transformersjs-v4`) and keeps Whisper KV-cache outputs (`present.*`) directly in `gpu-buffer` (`packages/transformers/src/models/session.js` L110–124) to avoid per-token GPU→CPU copies.
  - WebGPU requires a one-time WGSL shader compilation warm-up on first load; Hugging Face's official `whisper-word-timestamps/src/worker.js` runs a 1-second silent warm-up pass before signalling `ready`.
  - On our laptop CPU (Ryzen 7 PRO 250, 16 threads), `R-0028` (`whisper-small` ONNX q8) took **6.9–7.3 s** for a 3 s NCHLT clip and **9.0–9.4 s** for a 14.2 s founder clip in Chrome WASM (16 threads, COOP/COEP), vs **18.7 s** single-threaded (`R-0017`). `R-0037` measured native CTranslate2 int8 `R-0035` medium on the same laptop CPU at **7.72 s/clip** mean on FLEURS (and 7.1 s live for a 12.8 s clip, D-0033).
  - `whisper.cpp` v1.9.5 `examples/whisper.wasm/README.md` states `tiny`/`base` achieve only ~2–3× real-time on modern desktop CPUs in WASM, and explicitly rates models above `small` as **"unsatisfactory"** in both memory and performance.
- **Neon Inferences (NOT directly measured yet — must be verified in Step 3 of §7):**
  - **Ordinary laptop WITH WebGPU (e.g. Radeon 780M iGPU, Intel Iris Xe/Arc, Apple M-series, discrete GPU):** Because Whisper's 30 s encoder is heavy dense matrix multiplication (75% of CPU time in `R-0026`) and the decoder is memory-bandwidth bound, WebGPU with `q4f16` (or `fp16` encoder + `q4f16` decoder) should be **substantially faster than WASM CPU**, likely **~1–5 s** for a 12–15 s clip once shaders are compiled (after an initial ~5–15 s cold warm-up).
  - **Ordinary laptop WITHOUT WebGPU (WASM CPU fallback):** Scaling from `R-0028` small WASM (7–9 s/clip on 16 threads) by ~3.1× parameter/FLOP growth predicts **~20–30 s per clip** on a fast 16-thread laptop with COOP/COEP, and **~45–90 s** on an older 4-core laptop or single-threaded browser — too slow for a conversational demo.
  - **Mid-range phone (e.g. 4–6 GB RAM Android with Adreno/Mali GPU, or iPhone):** Even where WebGPU exists (Chrome Android 121+, Safari iOS 26+), mobile memory bandwidth is much lower and thermal throttling is aggressive, and **memory crashes (§2.2.D) are the primary blocker before compute speed**. Exact phone latency for `whisper-medium` `q4f16` is **UNVERIFIED**.

#### C. Browser Support (Verified 2026-11-20)

Exact matrix from `mdn/browser-compat-data` (`api/GPU.json`, `SharedArrayBuffer.json`, `CompressionStream.json`), WebKit Safari 26.0 release blog, Chrome 121 WebGPU blog, Firefox 141/145 release notes, and `transformers.js` 4.3.2:

| Browser / Platform | WebGPU (`navigator.gpu`) | Multi-threaded WASM (`SharedArrayBuffer` w/ COOP+COEP) | `CompressionStream('gzip')` (for JS loop guard) | Notes / caveats |
|---|---|---|---|---|
| **Chrome / Edge Desktop** | **Yes** (113+ Win/macOS/ChromeOS; 144+ Linux Intel Gen12+) | Yes (68+ / 79+) | Yes (80+) | Best-tested WebGPU target for ORT Web. |
| **Firefox Desktop** | **Partial** (141+ Windows; 145+ macOS Tahoe Apple Silicon; 147+ older macOS Apple Silicon; **No** Intel Mac, **No** Linux, **No** service workers) | Yes (79+) | Yes (113+) | `wgpu` backend; Linux/Intel-Mac users fall back to WASM. |
| **Safari macOS** | **Yes in Safari 26.0+** (older macOS/Safari: No) | Yes (15.2+) | Yes (16.4+) | `transformers.js` 4.3.0 (Sep 2026) enabled Safari 26+ WebGPU. |
| **Chrome Android** | **Yes in Chrome 121+** (Android 12+, Qualcomm & ARM GPUs) | Yes (89+) | Yes (80+) | Driver/adapter quality varies; older/budget Android phones may return `requestAdapter() === null`. |
| **Firefox Android** | **No** (`version_added: false` in MDN BCD) | Yes | Yes (113+) | WASM only. |
| **Safari iOS / iPadOS** (incl. Chrome/Firefox on iOS, which use WebKit) | **Yes in iOS 26.0+** (iOS < 26: No) | Yes (15.2+) | Yes (16.4+) | Memory/Jetsam limits remain strict (§2.2.D). |

- **Global coverage fact:** `transformers.js` 4.3.2 `guides/webgpu.md` notes global WebGPU support at **~85% as of March 2026** (citing `caniuse.com/webgpu`) — meaning ~15% of visitors still cannot run WebGPU at all.
- **Subtle feature-detection bug found in `transformers.js` 4.3.2 (`packages/transformers/src/env.js` L52):** `IS_WEBGPU_AVAILABLE` only tests `'gpu' in navigator` — it does **not** verify that `await navigator.gpu.requestAdapter()` succeeds (returns non-null), nor whether `adapter.features.has('shader-f16')` is true, nor whether `adapter.limits.maxBufferSize` is sufficient! And `models/session.js` L64–72 only checks `isWebGpuFp16Supported()` when `selectedDtype === 'fp16'`, not explicitly for `q4f16`. Our demo MUST run its own async adapter probe (§4).

#### D. Memory & Storage Limits (Source Facts + Inferences)
- **WebGPU buffer limits (W3C WebGPU spec, `gpuweb/gpuweb/spec/index.bs` L1817–1856):**
  - Default guaranteed `maxStorageBufferBindingSize`: **134,217,728 bytes (128 MiB)**.
  - Default guaranteed `maxBufferSize`: **268,435,456 bytes (256 MiB)**.
  - **Consequence for `whisper-medium` (Inference from R-0035 tensor shapes):** The single largest tensor is `embed_tokens` (`51,865 × 1,024` = 53.11M params): **212.44 MB in fp32** (exceeds the 128 MiB default storage-buffer binding limit!), vs **106.22 MB in fp16** (fits under 128 MiB) and ~26.6 MB if 4-bit quantized. Desktop WebGPU adapters commonly expose larger limits (e.g. 1–4 GB) when requested by ONNX Runtime Web, whereas constrained mobile GPUs may stay near 128–256 MiB — making `q4f16` significantly safer than `q4` (fp32 embeddings) on WebGPU.
- **WebAssembly linear memory (`v8.dev/blog/4gb-wasm-memory`):**
  - `wasm32` has a hard architectural ceiling of **4 GiB** ($2^{32}$ bytes; previously 2 GiB).
  - In `whisper.cpp` `examples/whisper.wasm/CMakeLists.txt`, Emscripten sets `MAXIMUM_MEMORY=2000MB` (2 GB) and `helpers.js` downloads the entire `.bin` into a JS `Uint8Array`, stores it in IndexedDB, writes it into Emscripten's in-memory filesystem (`FS_createDataFile`), and then `whisper_init_from_file_with_params` allocates ggml buffers (~2.1 GB for fp16 per `whisper.cpp` README L143) — a transient spike that easily blows 2 GB on medium.
- **Peak memory during ONNX load in `transformers.js` (Inference):** Fetching `decoder_model_merged_q4f16.onnx` (336 MB) + `encoder_model_q4f16.onnx` (181 MB) into JS `ArrayBuffer`s, parsing inside WASM, and uploading weights + KV cache + pooled GPU buffers (`onnxruntime.ai` WebGPU EP buffer cache modes) typically peaks at **~2–3× file size (~1.2–2.0 GB for `q4f16`; ~2.0–3.0 GB for `fp16`+`q4f16`)**. Desktop/laptop browsers with 8–16 GB RAM handle this cleanly; **mobile tabs on 4–6 GB phones and iOS Safari** face hard OS memory termination (**iOS Jetsam** kills the WebContent process silently with no JS exception caught).
- **Browser cache quotas & Safari's 7-day eviction trap (MDN Storage Quotas & WebKit Storage Policy blog `14403`):**
  - **Chrome / Edge:** Up to **60% of total disk per origin** (80% across all origins), evicted LRU only under disk pressure.
  - **Safari (macOS 14+ / iOS 17+):** Up to **60% of disk** for browser apps (15% for embedded webviews), **BUT** WebKit enforces a **7-day cap on all script-writable storage** (Cache API, IndexedDB, OPFS): if a user does not tap/click on that origin during 7 days of browser use, Safari deletes the cached model automatically. A casual Safari visitor would re-download 522 MB–956 MB on their next visit.

#### E. Accuracy Lost by Quantisation (Source Facts vs Inferences)
- **What primary sources show:**
  1. **Söhler, Irigoyen & Kirkedal (v2 May 2026, LREC SPEAKABLE, `arXiv:2511.08093`, Tables 2–3):** Evaluated post-training quantization on LibriSpeech `test-clean` and harder `test-other` (reporting both WER and CER) across `whisper-small`, `whisper-base`, and `whisper-tiny`:
     - On **clean speech (`test-clean`)**, 4-bit looks almost lossless on `whisper-small`: fp32 `3.48 WER / 1.02 CER` → `HQQ int4`: `3.52 / 1.09` (+0.07 CER); `BNB nf4`: `3.54 / 1.05` (+0.03 CER).
     - On **harder/noisy speech (`test-other`)**, 4-bit hurts markedly more: `whisper-small` fp32 `11.88 WER / 3.62 CER` → `BNB nf4`: **`13.49 / 4.05` (+1.61 WER / +0.43 CER)**; `HQQ int4`: **`14.09 / 4.38` (+2.21 WER / +0.76 CER)**.
     - **Size-scaling trend (Table 3 vs Table 2):** Smaller Whisper models degrade far worse under 4-bit (`BNB nf4` on `test-other`: `tiny` CER 12.84 → **20.20** [+7.36]; `base` 6.76 → **10.16** [+3.40]; `small` 3.62 → **4.05** [+0.43]).
     - **Static quantization fails badly on Whisper** (Table 2: Quanto static int8/fp8 jumped `small` `test-clean` WER from 3.48 → 5.95 and `test-other` from 11.88 → 15.92). Always use weight-only / dynamic quantization.
  2. **Andreyev (March 2025, `arXiv:2503.09905`, Table III):** Tested `whisper.cpp` `base` (NOT `medium`) on LibriSpeech: `q8_0`, `q5_0`, and `q4_0` all stayed around ~1.6–2.0% WER on clean speech. Too small a model and clean benchmark to extrapolate to isiXhosa `medium`.
  3. **Hugging Face `transformers.js` 4.3.2 `guides/dtypes.md` (explicit warning):** *"Some encoder-decoder models, like Whisper or Florence-2, are extremely sensitive to quantization settings: especially of the encoder."* Consistent with this warning, Hugging Face's own live WebGPU spaces and examples (`webml-community/whisper-large-v3-turbo-webgpu`, `transformers.js-examples/realtime-whisper-webgpu`, `whisper-word-timestamps`) **do NOT quantize the encoder to `q4`**: they set `encoder_model: "fp16"` (or `"fp32"`) and `decoder_model_merged: "q4"` on WebGPU, and `dtype: "q8"` on WASM.
  4. **Why `q8` is NOT used on WebGPU:** In `transformers.js` examples (`whisper-word-timestamps/src/worker.js`), `q8` is mapped strictly to `wasm`, while `webgpu` uses `fp32`/`fp16` + `q4` (ONNX `q8` dynamic quantization uses `DynamicQuantizeLinear`/`MatMulInteger`, whereas WebGPU acceleration targets `fp16`/`fp32` and `MatMulNBits` 4-bit weights).
  5. **Our own R-0035 int8 anchor (`R-0036`/`R-0037`):** CTranslate2 int8 cost **+0.19 to +0.35 CER** on 100 FLEURS clips (6.16–6.32 vs 5.97 GPU fp16), with zero loss on NCHLT.
- **Neon Inferences:**
  - Because larger models suffer less from 4-bit quantization than smaller ones (Söhler et al. Tables 2–3), `whisper-medium` (764M) is likely more resilient to 4-bit weights than `whisper-small` (244M) — **probably ~+0.3 to +0.8 CER on FLEURS/Swivuriso if `q4f16` encoder behaves stably**, which would still beat `R-0027` small (8.89 FLEURS / 5.25 Swivuriso) by a wide margin (>2.5 CER on FLEURS, >1.0 CER on Swivuriso).
  - **HOWEVER**, because `guides/dtypes.md` warns of encoder sensitivity and no benchmark exists for 4-bit ONNX `MatMulNBits` on isiXhosa `whisper-medium`, **both `q4f16`+`q4f16` (~522 MB) and `fp16`+`q4f16` (~956 MB) MUST be scored head-to-head on R-0035 before choosing** (§7).

#### F. Compatibility With Our Exact Setup (Line-by-Line Code Audit)

Audited directly in `huggingface/transformers.js@4.3.2` and `ggml-org/whisper.cpp@v1.9.5`:

| Requirement | `transformers.js` 4.3.2 (WebGPU / WASM) | `whisper.cpp` v1.9.5 (`whisper.wasm`) |
|---|---|---|
| Forced `language: "sw"`, `task: "transcribe"`, no timestamps (`<\|notimestamps\|>`) | **Supported natively** (`modeling_whisper.js` L47–91 builds `[<\|startoftranscript\|>, <\|sw\|>, <\|transcribe\|>, <\|notimestamps\|>]` from `generation_config.json` and call kwargs). | Core `whisper.h` supports `language="sw"`, `translate=false`, `no_timestamps=true`, **but** stock `emscripten.cpp` hardcodes `print_timestamps=true` and omits `no_timestamps=true` -> requires custom C++/Emscripten recompile. |
| Fine-tuned tokenizer & `generation_config.json` (`suppress_tokens`, `begin_suppress_tokens`) | **Supported natively** (`modeling_whisper.js` L130–133, `configuration_utils.js` L262–277). | `models/convert-h5-to-ggml.py` reads `vocab.json` & `added_tokens.json` but **does NOT read `generation_config.json` or `suppress_tokens`** (uses whisper.cpp's own `suppress_blank`/`suppress_nst` flags instead). |
| P-0015 `cache_position` export bug | **STILL PRESENT in v4.3.2!** `modeling_utils.js` L1355–1384 (`decoder_forward`) does NOT supply `cache_position`. We **must** continue exporting with `transformers==4.41.2` + `optimum==1.20.0` (as in `src/export_onnx.py`) so `cache_position` is not added to the decoder graph. | N/A (does not use ONNX). |
| Beam search (`num_beams: 5`) | **NOT IMPLEMENTED in v4.3.2!** `modeling_utils.js` L957 (`// NOTE: For now, we don't support spawning new beams`) and L1017 (`// TODO: Support beam search`). Greedy only. **Exact cost on R-0035:** +0.14 CER Swivuriso (3.38 vs 3.24), +0.35 CER FLEURS (5.56 vs 5.21), +0.07 CER NCHLT (1.99 vs 1.92) (`runs/R-0035/run.md`). | Core `whisper.h` supports `beam_size=5`, **but** stock `emscripten.cpp` hardcodes `WHISPER_SAMPLING_GREEDY` -> requires custom C++ edit + recompile. |
| Loop guard / repetition fallback (`compression_ratio > 2.4` → temperature 0.2/0.4/0.6) | **Not built in, but easy (~20 lines in `worker.js`):** `transformers.js` 4.3.2 DOES implement `do_sample: true` + `temperature` (`modeling_utils.js` L536–538 `TemperatureLogitsWarper`), and `CompressionStream('gzip')` is built into Chrome 80+, Firefox 113+, Safari 16.4+ (`mdn/browser-compat-data`). On any chunk whose `utf8Bytes.length / gzipBytes.length > 2.4`, retry at `temperature: 0.2`, `0.4`, `0.6` and keep the first `<= 2.4` (or lowest ratio), matching `src/live.py` L107–126 (1 sample per temp to stay fast). | Core `whisper.h` supports `entropy_thold` + `temperature_inc`, **not** exposed in stock `emscripten.cpp` without custom build. |
| Silence hallucination guard (Silero VAD, R-0023) | **Easy add-on:** `onnx-community/silero-vad` `model_quantized.onnx` is only **0.64 MB** (fp32 2.24 MB) and runs on WASM in milliseconds before Whisper, skipping pure silence and cutting long speech at pauses just like `src/live.py` L129–137. | Needs separate VAD integration in Emscripten. |
| ONNX 2 GiB protobuf limit when untying (`src/export_onnx.py`) | **Watch out during export:** `decoder_model_merged.onnx` fp32 for medium is **1,828.25 MB**. Adding untied `embed_tokens_T` in fp32 (+212.44 MB) reaches **2,040.69 MB** — just 107 MB under ONNX's 2 GiB (`2,147,483,648 B`) protobuf limit (`transformers.js@3.8.1/scripts/quantize.py` L211). Use `save_as_external_data=True` if saving intermediate untied fp32, and note `MatMul4BitsQuantizer` works directly on fp32 without untying if `embed_tokens` is left in fp16 (`q4f16`). | N/A. |

---

## 3. Route 2: Teaching `whisper-small` from `whisper-medium` (Distillation / Pseudo-Labelling)

### 3.1 The Mandatory Control First (Before Any Distillation)
Our current `whisper-small-isixhosa` (`R-0027`: Swivuriso 24.03 / 5.25, FLEURS 38.18 / 8.89) was trained with our **old buggy recipe** (4,000 steps / 1.3 epochs, checkpoint-3500 chosen on NCHLT dev with a 96-token output cap, no SpecAugment). On the exact same 309.7 h of data, fixing those four bugs on medium (`R-0029` → `R-0035`) reduced greedy WER by **2.61–3.16 points** and CER by **0.60–0.76 points** (`results.md` L45–46, L58–59).

**Inference:** Retraining `whisper-small` on our existing 309.7 h with **R-0035's fixed recipe alone** (plain supervised fine-tuning, no distillation) is the mandatory control. Until we run it, we do not know how much of `R-0027`'s deficit is just under-training + bad checkpoint selection.

### 3.2 What Published Work Shows About Closing the Gap

Three primary papers directly test the pieces relevant to us:

1. **Cross-size logit distillation on the SAME labelled low-resource data — Ferraz et al. (ICASSP 2024, `arXiv:2311.01070`, Tables 1–2):**
   - Distilled `whisper-large-v2` (1.5B, FLEURS avg WER **12.5**) into `whisper-small` (244M, zero-shot **28.3**) across 8 under-represented languages (Catalan, Czech, Galician, Hungarian, Polish, Tamil, Thai, Ukrainian).
   - **Result (Table 1, FLEURS OOD avg):** `whisper-small` + standard fine-tuning = **23.3 ± 0.06 WER**; `whisper-small` + CLSR + logit KD (`DistilWhisper`) = **22.8 ± 0.21 WER**.
   - **Result across data sizes (Table 2, FLEURS OOD avg across ca/ta/th):**
     - 3k utterances: FT **20.5** vs +KD **20.2** (-0.3 WER)
     - 10k utterances: FT **18.0** vs +KD **17.4** (-0.6 WER)
     - 28k utterances: FT **15.7** vs +KD **15.5** (-0.2 WER)
   - **Takeaway:** On a fixed labelled dataset, logit-level KD from a much stronger teacher into `whisper-small` yields a real but **modest gain of ~0.2–0.6 WER** over well-tuned supervised fine-tuning — closing only ~5% of the remaining ~10.8-point teacher-student gap.

2. **Why `whisper-small` hits an encoder-capacity ceiling — Gandhi et al. (`Distil-Whisper`, `arXiv:2311.00430`, Tables 5, 10, 11, 12) & Waheed et al. (`uDistil-Whisper`, v5 May 2025, `arXiv:2407.01257`, Table 12 on Swahili):**
   - In **Distil-Whisper Table 12**, keeping all 32 encoder layers while shrinking the decoder 32 → 4 layers moved OOD WER from **5.3 → 6.5** (+1.2 WER), whereas halving the encoder too (`16 enc / 2 dec`, 441M) jumped OOD WER to **10.5** (+5.2 WER).
   - In **uDistil-Whisper Table 12 (Swahili — a Bantu language related to isiXhosa, trained on >100 h labelled speech)**, distilling `Whisper-large-v2` (FLEURS OOD CER **14.8**) while keeping all 32 encoder layers (`UDW-32-16pr`, 1.12B) held FLEURS OOD CER at **14.9** (+0.1 CER), whereas halving the encoder (`UDW-16-16pr`, 0.80B) degraded FLEURS OOD CER to **18.5** (+3.7 CER) and AMMI-LigAikuma OOD CER from 13.0 → **18.5** (+5.5 CER).
   - **Distil-Whisper Table 11 (Data-size ablation):** Distilling a 2-layer decoder from `large-v2` with **435 h** (still more than our 309.7 h!) caused OOD WER to jump from **5.3 → 13.8** (+8.5 WER); it needed **3,483–21,770 h** of pseudo-labelled audio to reach 7.4–7.8 OOD WER.
   - **Distil-Whisper Table 10 & uDistil-Whisper (§4):** Filtering noisy pseudo-labels is mandatory. Without a WER filter, Distil-Whisper's OOD WER worsened from **7.3 → 9.1**; in uDistil-Whisper, skipping filtering worsened student WER by **+6 points** (64.2% vs 58.5% on 100k segments).

3. **Distil-Whisper's loss recipe (`huggingface/distil-whisper/training/run_distillation.py` L1046, L1484–1493):**
   - Uses `loss = 0.8 * ce_loss + kl_weight * kl_loss` with softmax temperature `T = 2.0` (scaled by `T^2`).
   - Crucially, `share_hidden_states` only works when `student.d_model == teacher.d_model` and `freeze_encoder=True` (same encoder width). Distilling `medium` (`d_model=1024`) → `small` (`d_model=768`) requires running **both** medium's encoder+decoder (frozen fp16) and small's encoder+decoder (training fp32) on every batch.

### 3.3 Estimated Data & AWS GPU Cost for This Project

Anchored to our measured run times (`R-0007`: small on L4 `g6.xlarge` [$0.805/h] = 1.94 s/step incl. evals; `R-0035`: medium on L40S `g6e.2xlarge` [$2.24/h] = 1.57 s/step; `g6e.xlarge` L40S = $1.861/h; scoring ~22 h of audio on L40S took ~25 min ≈ 50× real-time). Note: November 2026 GPU spend is already **~$17 of the $30 monthly brake** (`JOURNAL.md` L439), leaving **~$13** before the 1 December reset unless raised.

| Option | Data needed | GPU & estimated time (Inference from R-0007 / R-0035) | Estimated AWS cost | Expected accuracy impact vs current `R-0027` small (Inference) |
|---|---|---|---|---|
| **2A. Retrain `whisper-small` with R-0035 fixed recipe (no KD — mandatory control)** | Existing 309.7 h in S3 (no new data) | L4 (`g6.xlarge`, $0.805/h): ~5.5–6.2 h; **or L40S (`g6e.xlarge`, $1.861/h): ~2.3–2.8 h** (well inside 6 h cap) | **~$4.50–$5.20** | Largest per-dollar gain for small: likely **-2 to -3 WER / -0.5 to -0.9 CER** (comparable to `R-0029` → `R-0035` recipe jump), but still ~5–7 WER behind `R-0035` medium. |
| **2B. Online logit KD (`R-0035` medium → `small`) on existing 309.7 h** | Existing 309.7 h in S3 | L40S (`g6e.xlarge`, $1.861/h): ~4.0–4.8 h (9,000 steps, frozen fp16 medium forward + small train) | **~$7.50–$9.00** | Likely **only +0.2–0.6 WER better than 2A** (extrapolating Ferraz et al. Table 2). Does **not** close the 6–8 WER encoder gap. |
| **2C. Pseudo-labelling extra audio + student training** | Needs new audio: only candidates in project records are **NCHLT auxiliary** (~158 h, currently blocked by corrupt ZIP P-0017; already has transcripts of unknown quality) and Swivuriso's dropped `[?]` / non-a-z clips (~100+ h, noisy/unclear speech) | L40S ~3–4 h to pseudo-label 150–200 h (beam 5) + ~2.5–4.8 h student training | **~$11–$17** (exceeds remaining Nov brake room) | Uncertain/high risk without clean unlabelled audio + independent quality filter. |

### 3.4 Risks Specific to Low-Resource isiXhosa
1. **Teacher error locking (confirmation bias):** R-0035 still has 15.04% WER on Swivuriso, 26.06% on FLEURS, and 60.84% on Soapies code-switched speech (`runs/R-0035/run.md`). Pseudo-labelling unlabelled isiXhosa without human transcripts (or a strong independent filter like uDistil-Whisper's proxy/SONAR filter) teaches the student R-0035's exact systematic errors (over-eager English guesses on mixed speech, swallowed fast speech).
2. **No large clean unlabelled pool:** Distil-Whisper relied on 21,770 h of English audio. Swivuriso's unused `[?]` clips were dropped specifically because human annotators marked speech as unintelligible (`runs/R-0027/run.md` L11, L41) — dangerous pseudo-label material.
3. **Agglutinative morphology & encoder capacity:** Whisper's BPE tokenizer splits long isiXhosa words into many short subword tokens, and isiXhosa's click consonants (`c`/`q`/`x`) and breathy/aspirated contrasts lean heavily on acoustic encoder capacity. Both our own controlled size pairs (`R-0007`→`R-0012` and `R-0027`→`R-0029`) and the Swahili/multilingual papers confirm that `small`'s 12-layer encoder cannot match `medium`'s 24-layer encoder through distillation alone.

---

## 4. Route 3: Both — Hybrid / Progressive ("Small First, Optional High-Accuracy Medium")

This combines the reliability and phone reach of Small with the accuracy of R-0035 Medium on capable browsers:

1. **Default tier (every visitor, zero friction, phone-safe):**
   - Loads `whisper-small-isixhosa` (~295 MB `q8` on WASM, or WebGPU when available; later upgraded to fixed-recipe Small in Step C for the exact same ~295 MB download).
   - Works on all phones, Safari < 26, Firefox Linux/Android, and low-RAM laptops without crashing tabs or burning 500 MB–1 GB of mobile data unasked.
2. **Optional "High Accuracy (Medium · R-0035)" mode (user opt-in, gated by real capability checks):**
   - Instead of relying on `transformers.js`'s `'gpu' in navigator` check (`env.js` L52), run an explicit async probe before showing/enabling the toggle:
     ```js
     async function probeHighAccuracySupport() {
       if (!navigator.gpu) return { ok: false, reason: "no-webgpu" };
       const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
       if (!adapter) return { ok: false, reason: "no-adapter" };
       const hasF16 = adapter.features.has("shader-f16");
       const maxBuf = adapter.limits.maxBufferSize ?? 0;
       const maxBind = adapter.limits.maxStorageBufferBindingSize ?? 0;
       const est = navigator.storage?.estimate ? await navigator.storage.estimate() : null;
       const freeBytes = est ? (est.quota - est.usage) : Infinity;
       const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
       const lowMem = (navigator.deviceMemory ?? 8) < 4;
       // q4f16 needs shader-f16 + >=256 MiB buffer + >=128 MiB storage binding + ~1.5 GB quota margin
       const ok = hasF16 && maxBuf >= 268435456 && maxBind >= 134217728 && freeBytes >= 1.5e9 && !lowMem;
       return { ok, hasF16, isMobile, freeBytes, maxBuf, maxBind };
     }
     ```
   - **Explicit consent + honest size badge:** Show `"High accuracy · R-0035 (~522 MB once)"` (or `~956 MB` if `fp16` encoder is required). On mobile devices that pass WebGPU checks (Android 12+ Chrome, iOS 26+ Safari), either hide the option or label it `"Desktop recommended — may reload tab on phones"` until explicitly tested on real phones.
   - **Caching & cache visibility:** Use `transformers.js` v4.3.2's `is_pipeline_cached()` and `clear_pipeline_cache()` (`huggingface.co/blog/transformersjs-v4`) so visitors see whether Medium is already cached and can free disk space with one click; add a short note for Safari users if needed that Safari clears idle site caches after 7 days.
   - **Fail-safe disposal & fallback:** Before loading Medium, call `await smallPipeline.dispose()` so both models are never held in memory simultaneously. Wrap Medium load and inference in `try/catch` (plus `device.lost` awareness) so any WebGPU OOM cleanly disposes Medium, shows a plain-language notice, and falls back to Small WASM without stranding the user.
   - **Shared browser upgrades (benefit BOTH Small and Medium at $0):** Upgrade to `@huggingface/transformers@4.3.2`, add `onnx-community/silero-vad` int8 (**0.64 MB**) to skip silence and split at pauses, and add the ~20-line `CompressionStream('gzip')` loop guard (threshold 2.4, fallback temperatures `0.2`, `0.4`, `0.6`).

---

## 5. First-Principles Check: Does Any Other Route Clearly Beat These?

Judged strictly against our constraints: **free static Hugging Face Space ($0 hosting, no server GPU), on-device privacy, ~$30/month AWS credit cap, ~310 h of labelled isiXhosa speech.**

### 5.1 Distil-Whisper-Style Decoder Pruning on R-0035 Itself ("Thetha-Medium-Turbo": 24 enc + 4 dec)
- **Why this is the single most interesting alternative from first principles:**
  - From our exact header count of `data/models/R-0035/model.safetensors`: R-0035's **24-layer encoder is 307.2M params**, while its **24-layer decoder + embeddings is 456.6M tied (509.7M untied)** — **60–62% of the entire download size**!
  - Initializing a student with **R-0035's full 24-layer encoder (frozen)** + **4 maximally-spaced decoder layers** (copied from R-0035 layers `[0, 7, 15, 23]`) gives **307.2M + 67.3M + 53.1M = 427.6M tied params** (-44% total params, -74% decoder params, **~6× faster autoregressive decoding**).
  - **Download size anchor:** `distil-whisper/distil-medium.en` (24 enc + 2 dec, 394M) on HF Hub is 313.40 MB encoder + 88.92 MB decoder = **402.32 MB in `q8`**. By inference, a 24+4 pruned R-0035 would be **~430–485 MB in `q8`** and **~240–270 MB in `q4f16`** — **smaller than our current `whisper-small` q8 demo (295 MB)** while keeping R-0035's full 24-layer medium encoder!
  - **Training cost (Inference):** With `freeze_encoder=True` and `share_hidden_states=True` (`distil-whisper/training/run_distillation.py` L1046), only 4 decoder layers + embeddings train -> **~$5–$7 on one L40S**.
  - **Why it does NOT clearly beat Route 3 today (Critical Caveat):** Distil-Whisper Table 11 showed that training a 2-layer decoder with only **435 h** caused OOD WER to collapse from **5.3 → 13.8** (+8.5 WER). A 4-layer decoder initialized from R-0035's *already isiXhosa-trained* decoder and trained with `0.8*CE + 1.0*KL` on 309.7 h might avoid collapse — **or** it might still degrade badly on unseen FLEURS/Swivuriso sentences. **Verdict:** High-upside secondary R&D experiment (~$6) ONLY if Route 1's $0 `q4f16` medium proves too large (~956 MB `fp16` encoder required) or too slow in the browser.

### 5.2 LiteASR / Lite-Whisper (`arXiv:2502.20583`, natively supported in `transformers.js` 4.3.2)
- `LiteASR` (Kamahori et al., v2 Aug 2025) compresses Whisper's **encoder** via training-free PCA using ~100 calibration clips (`Table 5`), and `transformers.js` 4.3.2 already includes `LiteWhisperForConditionalGeneration` (`modeling_whisper.js` L514).
- **Why it loses for `whisper-medium`:** On `efficient-speech/lite-whisper-medium`, compressing the encoder cuts total parameters by only **11.8%** (762.3M → 672.0M for `lite-whisper-medium-fast`: encoder 305.7M → 215.3M, decoder **unchanged at 456.6M**). Worse, `arXiv:2502.20583` Table 4 shows stacking LiteASR with INT8 adds **+0.8 WER** (10.2 → 11.0), and Table 6 shows faster degradation under noise (SNR -0.9 dB: 18.2 → 24.9 WER). Poor trade-off vs 4-bit quantization or decoder pruning.

### 5.3 Smaller-but-Better Architectures (Checked & Ruled Out)
- **`openai/whisper-large-v3-turbo`** (32 enc + 4 dec, 809M; `onnx-community` `q4f16` = 369.97 + 193.51 = **563.48 MB**): Does **not** support isiXhosa (same 99 languages as stock Whisper, no `xh` in model card); fine-tuning 32 encoder layers costs more VRAM/GPU budget than medium while still being larger than medium `q4f16` (522 MB).
- **`nvidia/parakeet-tdt-0.6b-v3`** (600M FastConformer-TDT): Pretrained on **25 European languages only** (no isiXhosa or any African language in its Hugging Face card). Training an unfamiliar Bantu phonology from scratch on 310 h with no Bantu pretraining is a bad fit.
- **Moonshine (`moonshine-ai/moonshine`, `arXiv:2410.15608`):** Optimized for variable-length edge/WASM audio without 30 s zero-padding, **but** supports only 10 languages (English, Spanish, German, Mandarin, Japanese, Korean, Vietnamese, Tagalog, Ukrainian, Arabic) — **zero African languages / no isiXhosa**.
- **Meta Omnilingual CTC 300M / 1B:** Already empirically tested in **`R-0034`** — 1B lost to R-0019 on every fair test set (FLEURS digit-free CER 6.31 vs 5.49; Soapies 40.79 vs 27.08; Swivuriso 4.74 vs 3.92), and 300M was worse everywhere (`results.md` L55). R-0035 widened the lead further.

### 5.4 Free External GPU / API Hosting
- Hugging Face Docker/Gradio free CPU Spaces require PRO ($9/month, P-0014); free third-party inference tiers do not host custom 3 GB fine-tuned Whisper checkpoints at $0; and uploading audio to a server breaks Thetha's core privacy guarantee (`release/web/README.md`: *"nothing you record leaves your device"*).

---

## 6. Recommendation

**Adopt Route 3 (Hybrid / Progressive: Small default + optional High-Accuracy Medium on WebGPU), executed in two disciplined, gated phases:**

1. **Phase 1 — $0 Laptop Validation (do this FIRST, before spending any AWS credit or touching the public Space):**
   - Export `data/models/R-0035` to ONNX and quantize to `q4f16` (~522 MB), `fp16`+`q4f16` (~956 MB), `q4` (~684 MB), and `q8` (~829 MB).
   - Measure exact CER/WER on 100 FLEURS + 200 NCHLT unseen clips in Python `onnxruntime` and benchmark real WebGPU speed/memory in Chrome/Edge on the founder's Radeon 780M laptop using `@huggingface/transformers@4.3.2`.
   - **Decision branch from Phase 1:**
     - **If `q4f16`+`q4f16` (~522 MB) passes accuracy + browser bars:** Ship Route 3 (Small default + opt-in Medium `q4f16` on WebGPU + Silero VAD + JS gzip loop guard).
     - **If `q4f16` encoder fails accuracy, while `fp16` encoder + `q4f16` decoder (~956 MB) passes:** Still viable as a clearly labelled **"Desktop Wi-Fi High Accuracy (~960 MB)"** toggle, *and* this strongly motivates testing the 24+4 decoder-pruned R-0035 experiment later (~$6) to cut size back down.
     - **If browser WebGPU fails on speed/memory:** Skip Medium in the browser and invest ~$5 in Phase 2b (fixed-recipe Small).
2. **Phase 2b — Optional Small Upgrade (~$4.50–$5.20 AWS, after 1 Dec brake reset or founder OK):**
   - Retrain `whisper-small` on the existing 309.7 h using **R-0035's fixed recipe** (9,000 steps, SpecAugment, Swivuriso+FLEURS dev, 225-token dev cap). This upgrades **every phone and non-WebGPU user** at zero extra download cost (~250–295 MB).
   - Do **not** pay ~$8–$17 for cross-size distillation or pseudo-labelling into `small` unless fixed-recipe `small` is measured first and a clean extra unlabelled corpus (e.g. unpacked NCHLT auxiliary) is available.

---

## 7. Concrete Step-by-Step Test Plan for the Lead ($0 Laptop-First)

### Prerequisites & Safety Guardrails (P-0011, P-0013, P-0015)
- **RAM check before starting:** Exporting 3.06 GB fp32 `R-0035` to ONNX can peak at ~8–12 GB RAM. Close browsers and heavy apps so Windows reports **≥ 10 GB free RAM** (run one heavy step at a time per P-0013).
  - **Fallback if laptop OOMs during export:** Run Step 1 only on one AWS CPU node (`c7i.4xlarge`, 32 GB RAM, ~$0.68/h, ~15 min = **~$0.15**, just like `R-0031`), then pull the quantized `.onnx` files (~2 GB total) to the laptop.
- **Create an isolated export venv** (outside the repo, e.g. `C:\Users\ntlak\venvs\onnx-med`, so global Python's `transformers 4.46.3` / `ctranslate2 4.5.0` stays untouched):
  - Pin **`transformers==4.41.2`**, **`optimum==1.20.0`** (mandatory: avoids the `cache_position` decoder input that `transformers.js` 4.3.2 STILL does not supply — §2.2.F), **`onnx`**, **`onnx-ir`** (required by `onnxruntime 1.27.0` `matmul_nbits_quantizer.py` L18 — verified missing on global Python!), **`onnxconverter-common`** (for `float16.convert_float_to_float16`), **`onnxruntime==1.27.0`**, **`soundfile`**, **`jiwer`**.

### Step 1: Export `R-0035` & Build Candidate Quantizations ($0 laptop / ~$0.15 fallback)
1. Export fp32 ONNX from `data/models/R-0035` into scratch folder outside repo (e.g. `C:\Users\ntlak\isixhosa-speech-ai-data\onnx\R-0035-test`):
   - `optimum-cli export onnx --model data/models/R-0035 --task automatic-speech-recognition-with-past <out>`
   - **Verify immediately** with `onnxruntime.InferenceSession` that `decoder_model_merged.onnx` inputs do **NOT** include `cache_position` (matching `runs/R-0028/run.md` L8).
2. Build 4 quantized candidates using `onnxruntime.quantization.matmul_nbits_quantizer` (`MatMul4BitsQuantizer`, `block_size=32`, `is_symmetric=True`, `accuracy_level=4`, matching `transformers.js@3.8.1/scripts/quantize.py` L237–330) + `onnxconverter_common.float16.convert_float_to_float16(..., keep_io_types=True, disable_shape_infer=...)`:
   - **Candidate A (`q4f16` + `q4f16`):** `encoder_model_q4f16.onnx` + `decoder_model_merged_q4f16.onnx` (expected ~517 MB).
   - **Candidate B (`fp16` + `q4f16`):** `encoder_model_fp16.onnx` + `decoder_model_merged_q4f16.onnx` (expected ~951 MB).
   - **Candidate C (`q4` + `q4`):** `encoder_model_q4.onnx` + `decoder_model_merged_q4.onnx` (expected ~679 MB).
   - **Candidate D (`q8` + `q8`):** run `untie_output_layer()` from `src/export_onnx.py` (using `save_as_external_data=True` if close to 2 GiB protobuf cap) then `quantize_dynamic(..., QUInt8, ["MatMul", "Gather"], EnableSubgraph=True)` (expected ~829 MB; accuracy/WASM anchor).
3. Record exact byte sizes of every `.onnx` file (and gzipped size for transfer estimate).

### Step 2: Python ONNX Accuracy Benchmark ($0 laptop, ~20–35 min per candidate)
Extend `src/eval_onnx.py` (in a new run `R-0038`) to score **greedy + gzip loop guard (ratio > 2.4, temps 0.2/0.4/0.6)** on two fixed public subsets already on disk:
1. **100 FLEURS `xh_za` test clips (seed 1)** — exact same 100 clips as `R-0036`/`R-0037`! Compare against:
   - `R-0035` legacy greedy GPU predictions (`runs/R-0035/legacy_greedy/eval_fleurs/predictions.jsonl`, same 100 clips) — the fair greedy ceiling for `transformers.js`.
   - `R-0027` small ONNX `q8` on the same 100 clips — the current browser demo baseline!
2. **200 NCHLT unseen-sentence test clips (seed 1)** — exact same 200 clips as `R-0028` (`R-0027` ONNX `q8` = 35.49 WER / 6.07 CER) and `runs/R-0035/legacy_greedy/eval_nchlt/predictions.jsonl`.

*(Start with Candidate A [`q4f16`+`q4f16`] first! Only score B/C/D if A misses the bar or for comparison. Note: if ORT CPU has slow `fp16` ops for `q4f16`, test `q4` [C] on CPU or use ORT `DmlExecutionProvider` / Node WebGPU — record exact EP used!)*

**Pre-registered Accuracy Pass/Fail Bar (set BEFORE running):**
- **FLEURS 100 clips (seed 1):** Candidate CER **≤ R-0035 greedy GPU CER + 0.50** AND **at least 1.50 CER lower than `R-0027` small ONNX q8** on the exact same 100 clips; **0 runaway loops** after the gzip loop guard.
- **NCHLT 200 unseen clips (seed 1):** Candidate CER **≤ R-0035 greedy GPU CER + 0.40**.
- **Diagnostic rule:** If Candidate A (`q4f16`+`q4f16`) fails while Candidate B (`fp16` enc + `q4f16` dec) passes, that confirms encoder 4-bit sensitivity on R-0035 → decide with founder whether ~956 MB desktop-only opt-in is acceptable or pivot to fixed-recipe Small / 24+4 decoder pruning.

### Step 3: Real-Browser WebGPU + WASM Benchmark on Founder's Laptop ($0)
Build a local test harness (outside repo or unpushed scratch folder) serving:
- `@huggingface/transformers@4.3.2` (`dist/transformers.web.min.js`) + pinned `onnxruntime-web@1.31.0-dev.20260914-8d85527a0` (`ort-wasm-simd-threaded.asyncify.{mjs,wasm}` and fallback `ort-wasm-simd-threaded.{mjs,wasm}`) — all checksum-verified from npm.
- Local COOP/COEP HTTP server (same headers as `release/web/README.md`) serving the winning R-0035 ONNX files + `onnx-community/silero-vad` (`model_quantized.onnx`, 0.64 MB) + a `worker.js` implementing `CompressionStream('gzip')` loop guard + `probeHighAccuracySupport()`.
- Test in **Chrome** and **Edge** on the founder's Ryzen 7 PRO 250 / Radeon 780M laptop (and Firefox if installed):
  1. Verify `probeHighAccuracySupport()` reports `hasF16`, `maxBufferSize`, `maxStorageBufferBindingSize`, and `crossOriginIsolated === true`.
  2. Measure **cold load + shader warm-up time** and **warm load from `transformers-cache`**.
  3. Transcribe 5 fixed audio files: (a) 3 s NCHLT clip (`nchlt_xho_500m_0267`), (b) ~12.8 s FLEURS clip, (c) 14.2 s founder clip (`20261021-140009` if available), (d) a 25–28 s FLEURS clip, (e) 5 s of pure silence.
  4. Record: wall-clock latency per clip (WebGPU vs WASM), exact text parity vs Step 2 Python ORT, **peak tab + GPU process memory** in Chrome Task Manager across 5 consecutive transcriptions (checking for GPU buffer leaks), and clean fallback to Small WASM when WebGPU is simulated to fail.

**Pre-registered Browser Pass/Fail Bar (set BEFORE running):**
- **Latency (warm WebGPU on Radeon 780M):** 12–15 s clip transcribes in **≤ 8.0 s** (matching or beating `src/live.py` CPU's 7.1 s and `R-0028` Small WASM's 9.0–9.4 s).
- **Stability & Memory:** Peak tab + GPU process memory **≤ 2.5 GB**; **5/5 consecutive runs succeed** with no `GPUDeviceLostInfo`, no OOM, and no unbounded VRAM growth.
- **Correctness:** Exact text match (or ≤ 0.1 CER diff) vs Step 2 Python ORT on all 4 speech clips; **empty string** on the 5 s silence clip with Silero VAD enabled.
- **Download budget:** **≤ 600 MB** (`q4f16`+`q4f16`) for general desktop opt-in; **≤ 1,000 MB** (`fp16`+`q4f16`) only if explicitly labelled *"Desktop Wi-Fi only (~960 MB)"*.

### Step 4: Real-Device Phone Smoke Test ($0, before publishing)
- Serve the local test page over LAN (or an unlisted private/preview Space) and test on the founder's phone (Android Chrome and/or iOS Safari):
  1. Confirm the default **Small** path still loads and runs cleanly with `transformers.js` 4.3.2 + Silero VAD + gzip loop guard.
  2. Test whether the phone passes `probeHighAccuracySupport()` and whether opting into Medium survives 3 transcriptions without tab reload / Jetsam crash. If it crashes or takes >15 s/clip on phone, keep Medium gated to desktop devices only.

**Total estimated cost of Steps 1–4:** **$0** (or **~$0.15** if Step 1 ONNX export needs a temporary AWS CPU node due to laptop RAM).

---

## 8. Open Questions & Unverified Items

Things that could **not** be verified from public sources and must be settled empirically or by founder decision:

1. **Exact CER/WER of `R-0035` under 4-bit ONNX `MatMulNBits` (`q4f16` vs `fp16` encoder + `q4f16` decoder):** No public benchmark tests 4-bit ONNX quantization on fine-tuned isiXhosa Whisper-medium. Whether the encoder survives `q4f16` (522 MB) or requires `fp16` (956 MB) is the #1 unknown — answered at $0 by Step 2.
2. **Actual WebGPU latency and peak VRAM of `whisper-medium` in `transformers.js` 4.3.2:** No reproducible public benchmark exists for `whisper-medium` `q4f16` on `transformers.js` 4.3.2 across Radeon 780M iGPU, Apple Silicon, or mobile GPUs. Answered at $0 by Steps 3–4.
3. **Whether `q4f16` triggers WebGPU numerical issues on AMD RDNA3 (Radeon 780M) or Safari 26 Metal:** Hugging Face's `realtime-whisper-webgpu` worker (v3.7.1) carried a comment `('fp16' is broken)` on `decoder_model_merged`. Whether v4.3.2's rewritten C++ WebGPU runtime (`onnxruntime-web@1.31.x`) fully fixed fp16/q4f16 decoding on Windows D3D12 (AMD/Intel/NVIDIA) and Safari 26 Metal is **UNVERIFIED** — must be tested directly in Step 3.
4. **How much of `R-0027` Small's deficit is just the old recipe:** `whisper-small` has never been trained with R-0035's 9,000-step SpecAugment + Swivuriso/FLEURS dev recipe. Its true ceiling (~$5 to measure) is unknown.
5. **Whether 4-layer decoder pruning on R-0035 (24 enc + 4 dec) survives at 309.7 h:** Distil-Whisper Table 11 showed 2-layer collapse at 435 h on English from scratch, but 4 layers initialized from R-0035's isiXhosa-trained decoder has never been tested.
6. **Founder product decision:** What is the maximum acceptable opt-in download size for a South African visitor on desktop Wi-Fi — is ~522 MB fine? What about ~956 MB if the encoder must stay `fp16`?
7. **NCHLT auxiliary archive (P-0017):** Still un-extracted (~158 h in a corrupt-central-directory ZIP); its audio/transcript quality (and thus its value for future training or pseudo-labelling) remains unknown.

---

## 9. Claims Ledger (For Lead Verification)

Every factual claim in this report is mapped below to its exact verified primary source (all external URLs verified HTTP 200 on 2026-11-20). Items marked **Inference** are Neon's own calculations or extrapolations from the cited facts.

| # | Claim | Type | Verified Source |
|---|---|---|---|
| C-01 | `R-0035` `model.safetensors` has 763,857,920 tied params (encoder 307,216,384; decoder non-emb 403,531,776; `embed_tokens` `51865×1024` = 53,109,760; untied = 816,967,680) and size 3,055,544,304 B (3.06 GB); `R-0035-int8/model.bin` is 774,731,149 B (774.7 MB). | Repo Fact | Direct header inspection of `data/models/R-0035/model.safetensors` & directory listing of `data/models/R-0035*`; `data/models/R-0035/config.json` |
| C-02 | `R-0035` uses `language: "sw"` (`<\|sw\|>` id 50318), `task: "transcribe"` (50359), `return_timestamps: false` (`<\|notimestamps\|>` 50363), `forced_decoder_ids: null`, custom `suppress_tokens` & `begin_suppress_tokens`. | Repo Fact | `data/models/R-0035/generation_config.json`; `decisions.md` D-0007 |
| C-03 | `R-0035` beam-5 guarded scores: Swivuriso 15.04 / 3.24 (unscripted 13.4 / 2.8), FLEURS 26.06 / 5.21, NCHLT 11.11 / 1.92 (unseen 24.4 / 4.1), Soapies 60.84 / 25.98. Legacy greedy: Swivuriso 15.51 / 3.38, FLEURS 26.64 / 5.56, NCHLT 11.45 / 1.99 (unseen 25.5 / 4.3). | Repo Fact | `runs/R-0035/run.md` L121–138; `runs/R-0035/legacy_greedy/eval_{swivuriso,fleurs}/metrics.json`; `release/model-card-medium.md` L82–92 |
| C-04 | `R-0035` CT2 int8 costs +0.19 CER (`ct2 4.5.0`: 6.16 vs 5.97 GPU fp16 / 5.94 CPU fp32) to +0.35 CER (`ct2 4.8.1`: 6.32) on 100 FLEURS clips; 100 FLEURS clips (1,281 s audio) decoded in 772 s on 8 laptop threads; live 12.8 s clip in 7.1 s. | Repo Fact | `runs/R-0036/run.md` L26–32; `runs/R-0037/run.md` L20–35; `decisions.md` D-0033 |
| C-05 | `R-0027` (`whisper-small`) used the same 309.7 h as `R-0035` with the old 4,000-step recipe (kept step 3,500, NCHLT dev, 96-token dev cap, no SpecAugment); greedy scores: Swivuriso 24.03 / 5.25, FLEURS 38.18 / 8.89, NCHLT 21.56 / 3.37 (unseen 33.3 / 5.3); Soapies greedy int8 (R-0030): 71.48 / 32.80. | Repo Fact | `runs/R-0027/run.md` L16–18, L47–56; `results.md` L40–44; `docs/research/lead-verification-2026-11-19.md` L8, L22 |
| C-06 | `R-0028` ONNX q8 browser copy of `R-0027`: `encoder_model_quantized.onnx` 98.19 MB + `decoder_model_merged_quantized.onnx` 196.58 MB = 294.77 MB; scored 35.49 / 6.07 vs GPU fp16 35.49 / 5.91 (+0.16 CER) on 200 NCHLT unseen clips; Python CPU 2.99 s/clip; Chrome WASM 16 threads 6.9–7.3 s (3 s clip) / 9.0–9.4 s (14.2 s clip); 1-thread WASM (R-0017) 18.7 s. | Repo Fact | `runs/R-0028/run.md` L7, L13–14, L21–22, L30–31; `runs/R-0017/run.md` L24–25; HF API (`https://huggingface.co/Ntlakanipho/whisper-small-isixhosa/tree/main/onnx`) |
| C-07 | Matched-recipe pure model-size gap: `R-0007` vs `R-0012` (64.2 h) FLEURS 44.38/10.16 vs 37.83/8.03; `R-0027` vs `R-0029` (309.7 h) Swivuriso 24.03/5.25 vs 18.12/4.14 (3.90 w/o runaway) and FLEURS 38.18/8.89 vs 29.80/6.16. | Repo Fact | `results.md` L15, L22, L40–41, L45–46 |
| C-08 | Current Space is `sdk: static` (Docker/Gradio free CPU Spaces need PRO $9/mo, P-0014), sets COOP/COEP/CORP headers, self-hosts `@huggingface/transformers@3.0.2` (`transformers.min.js` + `ort-wasm-simd-threaded.jsep.wasm`), runs `device: "wasm"` `q8` greedy in `worker.js`, checks `caches.open("transformers-cache")`. | Repo Fact | `release/web/README.md` L6–15; `release/web/worker.js` L1–35; `release/web/index.html` L121; `release/publish_web.py` L22–23; `problems.md` P-0014 |
| C-09 | Laptop hardware/env: AMD Ryzen 7 PRO 250 (8C/16T), AMD Radeon 780M iGPU, 15.3 GB RAM (~4.3 GB free), Windows with Chrome & Edge, Python 3.12.10, `torch 2.12.1+cpu`, `transformers 4.46.3`, `ctranslate2 4.5.0`, `onnxruntime 1.27.0` (`matmul_nbits_quantizer.py` imports `onnx_ir`, currently absent). | Local Fact | Local inspection on 2026-11-20; `onnxruntime/quantization/matmul_nbits_quantizer.py` L18 |
| C-10 | `@huggingface/transformers` latest is **4.3.2** (npm 2026-10-27, GitHub 2026-10-28; v4 blog 2026-02-09; v4.0.0 2026-03-30; v4.3.0 2026-09-16 enabled Safari 26+ WebGPU; v4.3.2 exposed `getSupportedDevices()`). Rewritten C++ WebGPU runtime, `is_pipeline_cached`, `clear_pipeline_cache`, `useWasmCache`. | Source Fact | `https://registry.npmjs.org/@huggingface/transformers/4.3.2`; `https://github.com/huggingface/transformers.js/releases/tag/4.0.0`; `https://github.com/huggingface/transformers.js/releases/tag/4.3.0`; `https://github.com/huggingface/transformers.js/releases/tag/4.3.2`; `https://huggingface.co/blog/transformersjs-v4` |
| C-11 | `@huggingface/transformers@4.3.2` depends on `onnxruntime-web@1.31.0-dev.20260914-8d85527a0` (latest stable `onnxruntime-web@1.31.1`, 2026-10-26) and no longer bundles `.wasm` inside its npm tarball; `backends/onnx.js` L354–364 loads `ort-wasm-simd-threaded.asyncify.{mjs,wasm}` (28.75 MB uncompressed in 1.31.1), falling back to non-asyncify `.wasm` (14.85 MB) on Safari < 26 without WebGPU. | Source Fact | `https://registry.npmjs.org/@huggingface/transformers/4.3.2`; `https://registry.npmjs.org/onnxruntime-web/1.31.1`; `https://data.jsdelivr.com/v1/packages/npm/@huggingface/transformers@4.3.2`; `https://data.jsdelivr.com/v1/packages/npm/onnxruntime-web@1.31.1`; `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/src/backends/onnx.js` (L354–364) |
| C-12 | Exact ONNX medium file sizes: `onnx-community/whisper-medium-ONNX` `q4f16` 180.63 + 336.28 = 516.91 MB; `q4` 209.95 + 469.35 = 679.31 MB; `fp16` encoder 614.72 MB; `q8` 313.15 + 672.56 = 985.71 MB. `Xenova/whisper-medium` `q8` 313.47 + 462.66 = 776.13 MB. `onnx-community/whisper-small` `q8` 92.33 + 156.75 = 249.08 MB. `onnx-community/whisper-large-v3-turbo` `q4f16` 369.97 + 193.51 = 563.48 MB. `distil-whisper/distil-medium.en` `q8` 313.40 + 88.92 = 402.32 MB. `onnx-community/silero-vad` `q8` 0.64 MB / fp32 2.24 MB. | Source Fact | HF Hub listings verified 2026-11-20: `https://huggingface.co/onnx-community/whisper-medium-ONNX/tree/main/onnx`; `https://huggingface.co/Xenova/whisper-medium/tree/main/onnx`; `https://huggingface.co/onnx-community/whisper-small/tree/main/onnx`; `https://huggingface.co/onnx-community/whisper-large-v3-turbo/tree/main/onnx`; `https://huggingface.co/distil-whisper/distil-medium.en/tree/main/onnx`; `https://huggingface.co/onnx-community/silero-vad/tree/main/onnx` |
| C-13 | `transformers.js` 4.3.2 supports `language: "sw"`, `task: "transcribe"`, `return_timestamps: false`, `suppress_tokens`, `begin_suppress_tokens`, `do_sample`, `temperature`, `preferredOutputLocation: 'gpu-buffer'` for WebGPU KV cache; does **NOT** support beam search (`modeling_utils.js` L957, L1017) and does **NOT** supply `cache_position` (`modeling_utils.js` L1355–1384); `IS_WEBGPU_AVAILABLE` only checks `'gpu' in navigator` (`env.js` L52); `session.js` L64–72 only checks `isWebGpuFp16Supported()` when `selectedDtype === 'fp16'`. | Source Fact | `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/src/models/whisper/modeling_whisper.js` (L47–135); `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/src/models/modeling_utils.js` (L536–538, L957, L1017, L1355–1384); `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/src/models/session.js` (L64–72, L110–124); `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/src/env.js` (L52) |
| C-14 | `transformers.js` `guides/dtypes.md` warns Whisper is *"extremely sensitive to quantization settings: especially of the encoder."* Hugging Face's official Whisper WebGPU workers (`realtime-whisper-webgpu`, `whisper-word-timestamps`, `webml-community/whisper-large-v3-turbo-webgpu`) use `encoder_model: "fp16"`/`"fp32"` + `decoder_model_merged: "q4"` on WebGPU (with a 1 s warm-up pass) and `q8` on WASM; `realtime-whisper-webgpu` (v3.7.1) noted `('fp16' is broken)` on decoder. | Source Fact | `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/docs/source/guides/dtypes.md`; `https://github.com/huggingface/transformers.js-examples/blob/main/realtime-whisper-webgpu/src/worker.js`; `https://github.com/huggingface/transformers.js-examples/blob/main/whisper-word-timestamps/src/worker.js`; `https://huggingface.co/spaces/webml-community/whisper-large-v3-turbo-webgpu` |
| C-15 | `transformers.js` quantization recipe (`scripts/quantize.py` L211, L226–331 in v3.8.1) uses `MatMul4BitsQuantizer(block_size=32, is_symmetric=True, accuracy_level=4)` for `q4`, then `float16.convert_float_to_float16(..., keep_io_types=True)` for `q4f16`, disabling shape inference at ONNX's 2 GiB protobuf limit. | Source Fact | `https://github.com/huggingface/transformers.js/blob/3.8.1/scripts/quantize.py` (L209–331) |
| C-16 | Browser WebGPU support: Chrome/Edge 113+ (Linux Intel Gen12+ in 144+), Chrome Android 121+ (Android 12+, Qualcomm/ARM GPUs), Safari 26.0+ (macOS/iOS/iPadOS/visionOS), Firefox 141+ Windows / 145+ macOS Tahoe Apple Silicon / 147+ older macOS Apple Silicon (no Intel Mac, no Linux, no Firefox Android). `guides/webgpu.md` cites ~85% global caniuse support as of March 2026. `SharedArrayBuffer`: Chrome 68 / Edge 79 / Firefox 79 / Safari 15.2 / Chrome Android 89. `CompressionStream`: Chrome 80 / Firefox 113 / Safari 16.4. | Source Fact | `https://github.com/mdn/browser-compat-data/blob/main/api/GPU.json`; `https://github.com/mdn/browser-compat-data/blob/main/javascript/builtins/SharedArrayBuffer.json`; `https://github.com/mdn/browser-compat-data/blob/main/api/CompressionStream.json`; `https://developer.chrome.com/blog/new-in-webgpu-121`; `https://webkit.org/blog/17333/webkit-features-in-safari-26-0/`; `https://www.firefox.com/en-US/firefox/141.0/releasenotes/`; `https://www.firefox.com/en-US/firefox/145.0/releasenotes/`; `https://github.com/huggingface/transformers.js/blob/4.3.2/packages/transformers/docs/source/guides/webgpu.md` |
| C-17 | W3C WebGPU spec default limits: `maxStorageBufferBindingSize = 134,217,728 B` (128 MiB), `maxBufferSize = 268,435,456 B` (256 MiB). V8 `wasm32` ceiling: 4 GiB (up from 2 GiB). Browser storage: Chrome/Edge 60% disk per origin (80% overall, LRU eviction); Safari 60% disk browser apps (15% webviews) + **7-day eviction of script-writable storage** after inactivity. ORT WebGPU EP buffer cache modes (`onnxruntime.ai`). | Source Fact | `https://github.com/gpuweb/gpuweb/blob/main/spec/index.bs` (L1817–1856); `https://v8.dev/blog/4gb-wasm-memory`; `https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria`; `https://webkit.org/blog/14403/updates-to-storage-policy/`; `https://onnxruntime.ai/docs/execution-providers/WebGPU-ExecutionProvider.html` |
| C-18 | `whisper.cpp` v1.9.5 (2026-10-06): `ggml-medium-q5_0.bin` 539.21 MB, `q8_0` 823.37 MB, `fp16` 1,533.76 MB (~2.1 GB RAM per README L143). `examples/whisper.wasm/README.md` says it runs models up to `small` inclusive, beyond which memory and performance are unsatisfactory, and supports Greedy only. `CMakeLists.txt` caps `MAXIMUM_MEMORY=2000MB`; `emscripten.cpp` hardcodes greedy + `print_timestamps=true`; `convert-h5-to-ggml.py` does not read `generation_config.json`; `ggml-webgpu` exists in vendored `ggml/` but is not wired into `whisper.wasm`. | Source Fact | `https://huggingface.co/ggerganov/whisper.cpp/tree/main`; `https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.5`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/README.md` (L143); `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/examples/whisper.wasm/README.md`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/examples/whisper.wasm/CMakeLists.txt`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/examples/whisper.wasm/emscripten.cpp`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/examples/helpers.js`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/include/whisper.h`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/models/convert-h5-to-ggml.py`; `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/ggml/CMakeLists.txt` (L231–235); `https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/ggml/src/ggml-webgpu/ggml-webgpu.cpp` |
| C-19 | `candle` WASM Whisper example only demonstrates `tiny` CPU WASM; `sherpa-onnx` WASM ASR (`wasm/asr/CMakeLists.txt`) is CPU WASM (`INITIAL_MEMORY=512MB`, no WebGPU). | Source Fact | `https://github.com/huggingface/candle/blob/main/candle-wasm-examples/whisper/README.md`; `https://github.com/k2-fsa/sherpa-onnx/blob/master/wasm/asr/CMakeLists.txt` L40 |
| C-20 | Whisper quantization accuracy: Söhler et al. (v2 May 2026, `arXiv:2511.08093`, Tables 2–3) show `whisper-small` 4-bit loses +0.03 to +0.07 CER on `test-clean` but **+0.43 CER (`BNB nf4`) to +0.76 CER (`HQQ int4`)** (+1.61 to +2.21 WER) on `test-other`, with steeper degradation on `base` (+3.40 CER) and `tiny` (+7.36 CER), and poor static int8/fp8 results. Andreyev (Mar 2025, `arXiv:2503.09905`, Table III) tested `whisper.cpp` `base` only on clean LibriSpeech (~1.6–2.0% WER across `q4_0`/`q5_0`/`q8_0`). | Source Fact | `https://arxiv.org/html/2511.08093` (Tables 2–3); `https://arxiv.org/abs/2503.09905` (Table III) |
| C-21 | Distil-Whisper (`arXiv:2311.00430`): `distil-medium.en` (24 enc / 2 dec, 394M, 6.8× faster) got 11.1 short-form / 12.4 long-form OOD WER vs `small.en` (10.8 / 14.7) and `medium.en` (9.5 / 12.3) (Tables 3, 5). Table 10: WER filtering cut OOD WER 9.1 → 7.3. Table 11: at 435 h, OOD WER degraded to 13.8 (vs 7.4 at 21,770 h and 5.3 teacher). Table 12: cutting decoder 32→4 cost +1.2 OOD WER (5.3→6.5), cutting encoder 32→16 jumped OOD WER to 10.5. Loss in `run_distillation.py` L1493: `0.8 * ce_loss + kl_weight * kl_loss` (`T=2.0`); `share_hidden_states` requires matching `d_model` + frozen encoder (L1046). | Source Fact | `https://arxiv.org/html/2311.00430` (Tables 1, 3, 5, 10, 11, 12); `https://github.com/huggingface/distil-whisper/blob/main/training/run_distillation.py` L1046, L1484–1493 |
| C-22 | Multilingual DistilWhisper (`arXiv:2311.01070`, Ferraz et al., ICASSP 2024): distilling `whisper-large-v2` (12.5 FLEURS WER) into `whisper-small` on 8 under-represented languages moved FLEURS WER from 23.3 (FT) to 22.8 (+CLSR+KD) in Table 1, and improved FT by 0.2–0.6 WER across 3k/10k/28k utterances in Table 2. | Source Fact | `https://arxiv.org/html/2311.01070` (Tables 1–2) |
| C-23 | uDistil-Whisper (`arXiv:2407.01257`, Waheed et al., v5 May 2025): on Swahili (>100 h labelled), `UDW-32-16pr` (32 enc) preserved FLEURS OOD CER (14.8 → 14.9), while `UDW-16-16pr` (16 enc) degraded FLEURS OOD CER to 18.5 (+3.7 CER) and AMMI-LigAikuma to 18.5 (Table 12); removing pseudo-label filtering worsened WER by >6% (§4). | Source Fact | `https://arxiv.org/html/2407.01257` (§4, Table 12) |
| C-24 | LiteASR (`arXiv:2502.20583`, Kamahori et al., v2 Aug 2025) uses PCA on ~100 calibration clips (Table 5), degrades +0.8 WER when stacked with INT8 (Table 4) and faster in noise (Table 6); `efficient-speech/lite-whisper-medium-fast` shrinks encoder 305.68M → 215.31M while leaving decoder 456.64M unchanged (-11.8% total params). | Source Fact | `https://arxiv.org/html/2502.20583` (Tables 1, 4, 5, 6); `https://huggingface.co/efficient-speech/lite-whisper-medium` |
| C-25 | Alternative ASR language coverage: `openai/whisper-large-v3-turbo` has no `xh`; `nvidia/parakeet-tdt-0.6b-v3` covers 25 European languages only; `moonshine-ai/moonshine` (`arXiv:2410.15608`) covers 10 languages (no African languages); Meta Omnilingual CTC 300M/1B lost to R-0019 on all fair tests in `R-0034`. | Source / Repo Fact | `https://huggingface.co/openai/whisper-large-v3-turbo`; `https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3`; `https://github.com/moonshine-ai/moonshine/blob/main/README.md`; `https://arxiv.org/abs/2410.15608`; `results.md` L55 |
| C-26 | GPU pricing & remaining November budget: `g6.xlarge` L4 $0.805/h (`runs/R-0027/run.md` L35), `g6e.xlarge` L40S $1.861/h, `g6e.2xlarge` $2.24/h (`runs/R-0035/run.md` L85–86); `R-0007` small L4 step time 1.94 s/step (`runs/R-0007/run.md` L22); November spend ~$17 of $30 monthly brake (`JOURNAL.md` L439; `decisions.md` D-0025). | Repo Fact | `runs/R-0007/run.md` L22; `runs/R-0027/run.md` L35; `runs/R-0035/run.md` L85–86; `JOURNAL.md` L439; `decisions.md` D-0025 |
| C-27 | WebGPU latency (~1–5 s warm desktop), WASM medium latency (~20–30 s 16-thread laptop), peak load RAM (~2–3× file size), 24+4 pruned R-0035 ONNX size (~240–270 MB `q4f16`), and AWS cost estimates for 2A ($4.50–$5.20), 2B ($7.50–$9.00), 2C ($11–$17), and 24+4 pruning ($5–$7). | **Inference** | Neon's extrapolations from C-01, C-04, C-06, C-12, C-21, C-26; must be measured empirically before committing to production. |
