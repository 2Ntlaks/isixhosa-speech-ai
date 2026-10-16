"""Text normalisation and WER/CER, shared by every run so scores stay comparable.

Normalisation is deliberately light: lowercase, drop punctuation, collapse spaces. It does not touch spelling,
so a wrong click letter (c/q/x) or a wrongly split word still counts as an error.
"""
import re
import unicodedata

import jiwer

NORMALISATION = ("v1: drop [bracketed] tags (NCHLT's [s] non-speech marker), NFC, lowercase, "
                 "punctuation -> space (apostrophes kept), collapse whitespace")


def normalise(text):
    text = re.sub(r"\[[^\]]*\]", " ", text)  # NCHLT marks non-speech events like [s]; they are not words
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s']", " ", text)  # \w keeps letters in any script, digits and _
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def score(refs, hyps):
    """Corpus-level WER and CER in percent (errors summed over all clips, divided by total reference words/letters)."""
    refs = [normalise(r) for r in refs]
    hyps = [normalise(h) for h in hyps]
    return {"wer": 100 * jiwer.wer(refs, hyps), "cer": 100 * jiwer.cer(refs, hyps), "n": len(refs)}
