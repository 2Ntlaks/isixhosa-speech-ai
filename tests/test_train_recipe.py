"""R-0035 recipe options in src/train.py: the pure helpers (no model, no data files).

The heavier checks were run by hand on the laptop with whisper-tiny and tests/fixture_data.py (see runs/R-0035/run.md):
old vs new train.py with default flags gave bit-identical weights and logs; the recipe options ran end to end.
"""
import argparse
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("USE_TF", "0")  # a laptop with TensorFlow/Keras 3 installed breaks transformers 4.46 otherwise
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import train  # noqa: E402


def args(**kw):
    base = dict(epochs=None, max_steps=4000, batch_size=8, grad_accum=4, eval_every=1000)
    return argparse.Namespace(**{**base, **kw})


class Steps(unittest.TestCase):
    def test_default_is_max_steps(self):
        self.assertEqual(train.steps_for(args(), 98663), 4000)

    def test_epochs_round_up_to_a_whole_evaluation(self):
        # R-0029's data: 98,663 clips at 32 per step = 3,083.2 steps per epoch
        self.assertEqual(train.steps_for(args(epochs=2.5), 98663), 8000)  # 7,708 -> 8,000 (2.59 epochs)
        self.assertEqual(train.steps_for(args(epochs=2.9), 98663), 9000)  # 8,941 -> 9,000
        self.assertEqual(train.steps_for(args(epochs=0.001), 98663), 1000)


class Selection(unittest.TestCase):
    def test_auto_is_the_old_rule(self):
        self.assertEqual(train.selection_metric("auto", ["nchlt"]), ("cer", None))
        self.assertEqual(train.selection_metric("auto", ["nchlt", "fleurs"]), ("nchlt_cer", None))
        self.assertEqual(train.selection_metric("auto", ["nchlt", "fleurs", "soapies"]), ("soapies_cer", None))
        self.assertEqual(train.selection_metric("auto", ["nchlt", "fleurs", "swivuriso"]), ("nchlt_cer", None))

    def test_combined(self):
        self.assertEqual(train.selection_metric("swivuriso+fleurs", ["nchlt", "fleurs", "swivuriso"]),
                         ("combined_cer", ("swivuriso", "fleurs")))
        with self.assertRaises(SystemExit):
            train.selection_metric("swivuriso+fleurs", ["nchlt", "fleurs"])
        with self.assertRaises(SystemExit):
            train.selection_metric("soapies", ["nchlt", "fleurs"])

    def test_combined_trainer_adds_the_mean_only_on_the_all_sets_call(self):
        t = object.__new__(train.CombinedTrainer)
        t.combine = ("swivuriso", "fleurs")
        logged = []
        t.log = logged.append
        parent = {"eval_nchlt_cer": 3.0, "eval_swivuriso_cer": 4.0, "eval_fleurs_cer": 7.0}
        orig = train.Seq2SeqTrainer.evaluate
        train.Seq2SeqTrainer.evaluate = lambda self, *a, **k: dict(parent)
        try:
            self.assertEqual(t.evaluate()["eval_combined_cer"], 5.5)
            self.assertNotIn("eval_combined_cer", t.evaluate(metric_key_prefix="eval_fleurs"))
        finally:
            train.Seq2SeqTrainer.evaluate = orig
        self.assertEqual(logged, [{"eval_combined_cer": 5.5}])


class DevSample(unittest.TestCase):
    def clips(self):
        out = []
        for s, (n_free, n_read) in enumerate([(30, 30), (3, 40), (40, 2), (0, 10)]):
            out += [{"id": f"s{s}u{i}", "speaker": f"s{s}", "type": "unscripted"} for i in range(n_free)]
            out += [{"id": f"s{s}r{i}", "speaker": f"s{s}", "type": "scripted"} for i in range(n_read)]
        return out

    def test_stratified_by_speaker_and_type(self):
        got = train.swivuriso_dev_sample(self.clips(), 22, 42)
        per = {}
        for c in got:
            per.setdefault(c["speaker"], {"unscripted": 0, "scripted": 0})[c["type"]] += 1
        self.assertEqual(per["s0"], {"unscripted": 11, "scripted": 11})
        self.assertEqual(per["s1"], {"unscripted": 3, "scripted": 19})   # few unscripted: topped up with scripted
        self.assertEqual(per["s2"], {"unscripted": 20, "scripted": 2})   # few scripted: topped up with unscripted
        self.assertEqual(per["s3"], {"unscripted": 0, "scripted": 10})   # small speaker: all of it
        self.assertEqual(got, train.swivuriso_dev_sample(self.clips(), 22, 42))  # seeded
        self.assertEqual([c["id"] for c in got], sorted(c["id"] for c in got))


if __name__ == "__main__":
    unittest.main()
