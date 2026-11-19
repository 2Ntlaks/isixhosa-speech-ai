"""Evaluator contracts (R-0033, R-0034) on synthetic data: no model weights, no network.

  .venv/Scripts/python -m unittest discover -s tests
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

os.environ.setdefault("USE_TF", "0")  # a laptop with TensorFlow/Keras 3 installed breaks transformers 4.46

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
import eval_guarded  # noqa: E402
import eval_omni  # noqa: E402
import fixture_data  # noqa: E402
import make_ct2  # noqa: E402
import testsets  # noqa: E402

PY = sys.executable


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = fixture_data.build(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def set_args(self, kind):
        p = self.p
        return {"nchlt": ["--xml", p["nchlt_test"], "--root", p["root"], "--train-xml", p["nchlt_train"]],
                "fleurs": ["--fleurs-tsv", p["fleurs_test"], "--fleurs-audio", os.path.join(p["fleurs_audio"], "test"),
                           "--train-fleurs-tsv", p["fleurs_train"]],
                "swivuriso": ["--swivuriso-tsv", p["swiv_test"], "--swivuriso-audio", p["swiv_audio"]],
                "soapies": ["--soapies-root", p["soapies"]]}[kind]


class TestSets(Fixture):
    def test_every_format_loads_and_reports_zero_errors_on_its_own_text(self):
        for kind in ("nchlt", "fleurs", "swivuriso", "soapies"):
            with self.subTest(kind=kind):
                out = os.path.join(self.tmp.name, "dry_" + kind)
                r = subprocess.run([PY, str(ROOT / "src" / "eval_omni.py"), "--dry-run", "--out", out]
                                   + self.set_args(kind), capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                m = json.load(open(os.path.join(out, "metrics.json"), encoding="utf-8"))
                self.assertEqual((m["wer"], m["cer"], m["exact_match_pct"]), (0.0, 0.0, 100.0))
                preds = [json.loads(l) for l in open(os.path.join(out, "predictions.jsonl"), encoding="utf-8")]
                self.assertEqual(len(preds), m["clips"])
                self.assertTrue(all("path" not in p for p in preds))
                if kind == "fleurs":
                    self.assertEqual(m["left_out_over_max_seconds"], 1)  # the 31 s fixture clip
                    self.assertIn("by_text_in_training", m)
                if kind == "swivuriso":
                    self.assertIn("per_type", m)
                if kind == "soapies":
                    self.assertEqual(m["word_hits"]["eng"]["pct"], 100.0)
                    self.assertEqual(m["cer_no_spaces"], 0.0)

    def test_longest_keeps_the_longest_clips(self):
        a = argparse.Namespace(xml=None, fleurs_tsv=None, swivuriso_tsv=self.p["swiv_test"], soapies_root=None,
                               swivuriso_audio=self.p["swiv_audio"], max_seconds=30.0, limit=0, sample=0,
                               sample_seed=1, longest=2)
        with contextlib.redirect_stdout(io.StringIO()):
            got = testsets.load(a)[1]
            a.longest = 0
            every = testsets.load(a)[1]
        self.assertEqual([c["duration"] for c in got], sorted((c["duration"] for c in every), reverse=True)[:2])

    def test_sample_is_seeded_ordered_and_the_same_for_every_evaluator(self):
        a = argparse.Namespace(xml=None, fleurs_tsv=None, swivuriso_tsv=self.p["swiv_test"], soapies_root=None,
                               swivuriso_audio=self.p["swiv_audio"], max_seconds=30.0, limit=0, sample=3,
                               sample_seed=1)
        with contextlib.redirect_stdout(io.StringIO()):
            first = [c["id"] for c in testsets.load(a)[1]]
            again = [c["id"] for c in testsets.load(a)[1]]
            a.sample = 0
            every = [c["id"] for c in testsets.load(a)[1]]
        self.assertEqual(first, again)
        self.assertEqual(len(first), 3)
        self.assertEqual(first, [i for i in every if i in first])  # original order kept

    def test_exactly_one_test_set(self):
        a = argparse.Namespace(xml="x", fleurs_tsv="y", swivuriso_tsv=None, soapies_root=None)
        with self.assertRaises(SystemExit):
            testsets.kind_of(a)

    def test_token_limits_are_the_earlier_runs(self):
        self.assertEqual(testsets.DEFAULT_MAX_NEW_TOKENS, {"nchlt": 96, "fleurs": 225, "swivuriso": 440, "soapies": 96})


class GuardedRules(unittest.TestCase):
    def options(self, *argv, kind="fleurs"):
        ap = argparse.ArgumentParser()
        eval_guarded.add_decode_args(ap)
        return eval_guarded.decode_options(ap.parse_args(list(argv)), kind)

    def test_defaults_are_whispers_reliability_rules(self):
        o = self.options()
        self.assertEqual(o["beam_size"], 5)
        self.assertEqual(o["temperature"], (0.0, 0.2, 0.4, 0.6))
        self.assertEqual((o["compression_ratio_threshold"], o["log_prob_threshold"], o["no_speech_threshold"]),
                         (2.4, None, None))  # fallback fires on loops only (Neon pre-flight)
        self.assertEqual((o["repetition_penalty"], o["no_repeat_ngram_size"]), (1.0, 0))
        self.assertEqual((o["condition_on_previous_text"], o["without_timestamps"], o["language"], o["task"]),
                         (False, True, "sw", "transcribe"))
        self.assertEqual((o["best_of"], o["vad_filter"], o["max_new_tokens"]), (5, False, 225))
        self.assertEqual(self.options(kind="swivuriso")["max_new_tokens"], 440)

    def test_every_setting_is_a_flag(self):
        o = self.options("--beam-size", "3", "--temperatures", "0,0.5", "--compression-ratio-threshold", "none",
                         "--log-prob-threshold", "-2", "--no-speech-threshold", "off", "--condition-on-previous-text",
                         "--with-timestamps", "--vad-filter", "--max-new-tokens", "100", "--language", "en")
        self.assertEqual((o["beam_size"], o["temperature"], o["compression_ratio_threshold"], o["log_prob_threshold"],
                          o["no_speech_threshold"], o["condition_on_previous_text"], o["without_timestamps"],
                          o["vad_filter"], o["max_new_tokens"], o["language"]),
                         (3, (0.0, 0.5), None, -2.0, None, True, False, True, 100, "en"))

    def test_retry_rule_matches_faster_whisper(self):
        o = self.options("--log-prob-threshold", "-1.0", "--no-speech-threshold", "0.6")  # Whisper's full rule
        ok = {"compression_ratio": 1.4, "avg_logprob": -0.3, "no_speech_prob": 0.0}
        self.assertFalse(eval_guarded.needs_retry(ok, o))
        self.assertTrue(eval_guarded.needs_retry({**ok, "compression_ratio": 2.5}, o))
        self.assertTrue(eval_guarded.needs_retry({**ok, "avg_logprob": -1.2}, o))
        self.assertFalse(eval_guarded.needs_retry({**ok, "avg_logprob": -1.2, "no_speech_prob": 0.9}, o))  # silence
        self.assertTrue(eval_guarded.needs_retry({**ok, "compression_ratio": 2.5, "no_speech_prob": 0.9}, o))

    def test_attempt_log_records_each_try_and_passes_calls_through(self):
        inner = types.SimpleNamespace(
            is_multilingual=True,
            generate=lambda *a, **k: [types.SimpleNamespace(sequences_ids=[[1, 2, 3]], scores=[-0.4],
                                                            no_speech_prob=0.01)])
        log = eval_guarded.AttemptLog(inner)
        log.generate("enc", [[0]], beam_size=5, patience=1.0, length_penalty=1.0)
        log.generate("enc", [[0]], beam_size=1, num_hypotheses=5, sampling_temperature=0.4, length_penalty=1.0)
        self.assertTrue(log.is_multilingual)
        self.assertEqual([a["temperature"] for a in log.attempts], [0.0, 0.4])
        self.assertAlmostEqual(log.attempts[0]["avg_logprob"], -0.4 * 3 / 4)  # faster-whisper's formula


class OmniContract(Fixture):
    def test_package_receives_one_mono_16k_float_clip_at_a_time_with_the_language_code(self):
        calls = []

        class Pipe:
            def transcribe(self, inp, lang=None, batch_size=1):
                calls.append((inp, lang, batch_size))
                return ["Alpha, Beta’s!"] * len(inp)

        out = os.path.join(self.tmp.name, "omni_contract")
        argv = ["eval_omni.py", "--model-card", "omniASR_CTC_300M_v2", "--out", out, "--sample", "2",
                "--soapies-root", self.p["soapies"]]
        with patch.object(sys, "argv", argv), patch.object(eval_omni, "load_pipeline", return_value=Pipe()), \
                patch("importlib.metadata.version", return_value="test"), contextlib.redirect_stdout(io.StringIO()):
            eval_omni.main()
        self.assertEqual(len(calls), 3)  # warm-up + 2 clips
        for inp, lang, bs in calls:
            self.assertEqual((len(inp), lang, bs), (1, None, 1))  # CTC: no language code
            w = inp[0]["waveform"]
            self.assertEqual((inp[0]["sample_rate"], w.ndim, w.dtype), (16000, 1, np.float32))  # Soapies is 32 kHz
        m = json.load(open(os.path.join(out, "metrics.json"), encoding="utf-8"))
        self.assertEqual(m["model"], "omniASR_CTC_300M_v2")
        self.assertEqual(m["language"], "none")
        preds = [json.loads(l) for l in open(os.path.join(out, "predictions.jsonl"), encoding="utf-8")]
        self.assertTrue(all(p["hyp"] == "Alpha, Beta's!" and p["hyp_raw"] == "Alpha, Beta’s!" for p in preds))
        self.assertEqual(m["outputs_with_curly_apostrophes"], 2)
        self.assertIn("score_without_apostrophe_mapping", m)
        self.assertEqual(m["diagnostics"]["outputs_with_non_ascii"], 0)  # counted after the mapping


class CompareAndConvert(Fixture):
    def test_compare_runs_labels_and_older_metrics_without_speaker_groups(self):
        a, b = os.path.join(self.tmp.name, "cmp_a"), os.path.join(self.tmp.name, "cmp_b")
        for d in (a, b):
            subprocess.run([PY, str(ROOT / "src" / "eval_omni.py"), "--dry-run", "--out", d]
                           + self.set_args("soapies"), check=True, capture_output=True)
        m = json.load(open(os.path.join(b, "metrics.json")))
        for k in ("per_speaker", "exact_match_pct", "language"):  # what src/eval_soapies.py never wrote
            m.pop(k)
        json.dump(m, open(os.path.join(b, "metrics.json"), "w"))
        os.remove(os.path.join(b, "samples.md"))  # src/eval_soapies.py never wrote one either (F-16): b goes first
        r = subprocess.run([PY, str(ROOT / "src" / "compare_runs.py"), f"old={b}", f"new={a}"], capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = json.loads(r.stdout)
        self.assertEqual(set(rep["runs"]), {"new", "old"})
        self.assertEqual(rep["runs"]["old"]["exact_match_pct"], 100.0)
        self.assertEqual(rep["runs"]["old"]["per_speaker_cer"], rep["runs"]["new"]["per_speaker_cer"])

    def test_incomplete_ct2_copy_is_refused(self):
        d = os.path.join(self.tmp.name, "ct2")
        os.makedirs(d, exist_ok=True)
        for f in ("config.json", "model.bin", "vocabulary.json"):  # what the converter alone writes (P-0020)
            open(os.path.join(d, f), "w").close()
        with self.assertRaisesRegex(SystemExit, "preprocessor_config.json"):
            make_ct2.check(d)

    def test_revision_must_be_pinned(self):
        with self.assertRaisesRegex(SystemExit, "pin a full commit"):
            make_ct2.fetch("Ntlakanipho/whisper-medium-isixhosa", "main", "ct2-int8", self.tmp.name)


if __name__ == "__main__":
    unittest.main()
