"""Thetha as a drop-in recognizer for the Siyamthanda translator (a friend's project; tested only on a copy).

Same interface as Siyamthanda's MetaTranslator (translator/meta_pipeline.py): audio -> isiXhosa text -> NLLB -> English,
with the stage texts and times kept on the object for the benchmark. Only the recognizer changes: Thetha (a Whisper
fine-tune, CTranslate2 int8 folder with tokenizer.json) through faster-whisper instead of Meta's Omnilingual CTC model.
Sentence-form restoration and NLLB are Siyamthanda's own code, unchanged.

Copy this file into the copy's translator/ folder. Thetha writes isiXhosa under the <|sw|> tag (D-0007), so the
recognizer is asked for language "sw" and task "transcribe"; NLLB is still told the text is isiXhosa ("xh").
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from translator.meta_pipeline import RESTORE_LANGUAGES, NllbTranslator, restore_sentence

THETHA_LANGUAGES = frozenset({"xh"})


class ThethaTranslator:
    def __init__(self, model_dir: Path, cpu_threads: int = 4, *, asr_threads: int = 8, beam_size: int = 1,
                 mt_backend: str = "ct2", mt_beam_size: int = 4, mt_model: str = "nllb-600m",
                 restore: bool = True) -> None:
        from faster_whisper import WhisperModel

        self.model_dir = Path(model_dir)
        self.beam_size = beam_size
        self.asr = WhisperModel(str(self.model_dir), device="cpu", compute_type="int8",
                                cpu_threads=asr_threads, num_workers=1, local_files_only=True)
        self.mt = NllbTranslator(cpu_threads, backend=mt_backend, beam_size=mt_beam_size, model=mt_model)
        self.restore = restore
        self.truecase_forms = None  # Siyamthanda's capitalization table is Afrikaans-only
        self.last_transcript = ""
        self.last_mt_input = ""
        self.last_asr_ms = 0.0
        self.last_decode_ms = 0.0
        self.last_translation_ms = 0.0

    def decoder_description(self, language: str) -> str:
        return f"thetha {self.model_dir.name}, faster-whisper beam {self.beam_size}, lang sw, task transcribe"

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.asr.transcribe(
            audio, task="transcribe", language="sw", beam_size=self.beam_size, best_of=1, temperature=0.0,
            condition_on_previous_text=False, without_timestamps=True, vad_filter=False)
        return " ".join(segment.text.strip() for segment in segments).strip()

    def translate(self, audio: np.ndarray, language: str, cancelled=None) -> str:
        if language not in THETHA_LANGUAGES:
            raise ValueError(f"Thetha recognizes isiXhosa only, not {language!r}")
        started = time.perf_counter()
        self.last_transcript = self.transcribe(audio)  # faster-whisper decodes lazily: time covers the whole decode
        self.last_asr_ms = (time.perf_counter() - started) * 1000
        self.last_decode_ms = 0.0
        self.last_translation_ms = 0.0
        self.last_mt_input = self.last_transcript
        if self.restore and language in RESTORE_LANGUAGES:
            self.last_mt_input = restore_sentence(self.last_transcript)
        if not self.last_mt_input:
            return ""
        started = time.perf_counter()
        english = self.mt.translate(self.last_mt_input, language)
        self.last_translation_ms = (time.perf_counter() - started) * 1000
        return english
