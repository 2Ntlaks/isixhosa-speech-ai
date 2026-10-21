"""Inference scheduling contracts, without loading weights or accessing the network."""
import contextlib
import io
import json
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import live


class Processor:
    def __init__(self, config="same"):
        self.feature_extractor = types.SimpleNamespace(to_json_string=lambda: config)
        self.tokenizer = types.SimpleNamespace(convert_tokens_to_ids=lambda tokens: list(range(len(tokens))))
        self.calls = []

    def __call__(self, pieces, **kwargs):
        assert live.lock.locked(), "feature extraction must hold the work lock"
        self.calls.append([piece.copy() for piece in pieces])
        return types.SimpleNamespace(input_features=torch.tensor([[float(x[0])] for x in pieces]))

    def batch_decode(self, outputs, **kwargs):
        return [f"chunk {int(output[0])}" for output in outputs]


class CT2Model:
    def __init__(self):
        self.calls = []

    def generate(self, features, prompts, **kwargs):
        self.calls.append((len(features), prompts, kwargs))
        return [types.SimpleNamespace(sequences_ids=[[int(row[0])]]) for row in features]


class TransformersModel:
    def __init__(self):
        self.calls = []

    def generate(self, features, **kwargs):
        self.calls.append(kwargs)
        return features.to(torch.int64)


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(live, "CHUNK", 4))
        self.stack.enter_context(patch.object(live, "CHUNK_BATCH_SIZE", 1))
        self.stack.enter_context(patch.object(live, "lock", threading.Lock()))
        self.stack.enter_context(patch.object(live, "WhisperForConditionalGeneration", TransformersModel))
        ct2 = types.SimpleNamespace(StorageView=types.SimpleNamespace(from_array=lambda x: x))
        self.stack.enter_context(patch.dict(sys.modules, {"ctranslate2": ct2}))
        self.audio = np.repeat(np.arange(1, 4, dtype=np.float32), 4)[:-2]

    def engines(self, entries):
        def load(name):
            self.assertTrue(live.lock.locked(), "lazy model loading must also be serialized")
            return entries[name]
        self.stack.enter_context(patch.object(live, "model", side_effect=load))

    def test_order_partial_tail_and_bounded_calls(self):
        proc, model = Processor(), CT2Model()
        self.engines({"medium": (proc, model)})
        text, seconds = live.transcribe(self.audio, "medium")
        self.assertEqual(text, "chunk 1 chunk 2 chunk 3")
        self.assertEqual([len(c[0]) for c in proc.calls], [4, 4, 2])
        self.assertEqual([c[0] for c in model.calls], [1, 1, 1])
        self.assertTrue(all(c[2] == {"beam_size": 5, "max_length": 225} for c in model.calls))
        self.assertGreaterEqual(seconds, 0)

    def test_compatible_compare_features_are_shared_but_not_across_requests(self):
        first, second = Processor(), Processor()
        self.engines({"medium": (first, CT2Model()), "small": (second, CT2Model())})
        result = live.transcribe_models(self.audio, ["medium", "small", "small"])
        self.assertEqual(result["medium"][0], result["small"][0])
        self.assertEqual(len(first.calls), 3)
        self.assertEqual(len(second.calls), 0)
        live.transcribe(self.audio + 10, "medium")
        self.assertEqual(len(first.calls), 6)

    def test_incompatible_feature_configurations_are_not_shared(self):
        first, second = Processor("80 mels"), Processor("128 mels")
        self.engines({"a": (first, CT2Model()), "b": (second, CT2Model())})
        live.transcribe_models(self.audio, ["a", "b"])
        self.assertEqual((len(first.calls), len(second.calls)), (3, 3))

    def test_batch_override_and_transformers_generation_contract(self):
        proc, model = Processor(), TransformersModel()
        self.engines({"hf": (proc, model)})
        with patch.object(live, "CHUNK_BATCH_SIZE", 2):
            self.assertEqual(live.transcribe(self.audio, "hf")[0], "chunk 1 chunk 2 chunk 3")
        self.assertEqual([len(call) for call in proc.calls], [2, 1])
        self.assertTrue(all(c == {"language": "sw", "task": "transcribe", "max_new_tokens": 225}
                            for c in model.calls))

    def test_failure_releases_lock_and_empty_audio_is_rejected(self):
        proc, model = Processor(), CT2Model()
        self.engines({"a": (proc, model)})
        with patch.object(model, "generate", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                live.transcribe(self.audio, "a")
        self.assertFalse(live.lock.locked())
        self.assertEqual(live.transcribe(self.audio, "a")[0], "chunk 1 chunk 2 chunk 3")
        with self.assertRaisesRegex(ValueError, "empty audio"):
            live.transcribe(np.array([], dtype=np.float32), "a")

    def test_waiting_request_does_not_prepare_features(self):
        proc, model = Processor(), CT2Model()
        self.engines({"a": (proc, model)})
        started = threading.Event()
        errors = []

        def request():
            started.set()
            try:
                live.transcribe(self.audio, "a")
            except Exception as error:
                errors.append(error)

        with live.lock:
            worker = threading.Thread(target=request)
            worker.start()
            self.assertTrue(started.wait(1))
            self.assertFalse(proc.calls)
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(errors)
        self.assertEqual(len(proc.calls), 3)

    def test_http_comparison_response_and_public_logging_stay_compatible(self):
        handler = object.__new__(live.Handler)
        handler.path = "/transcribe?model=a&also=b&keep=0"
        handler.headers = {"Content-Length": "3"}
        handler.rfile = io.BytesIO(b"wav")
        responses = []
        handler.send = lambda *args: responses.append(args)
        stdout = io.StringIO()
        with patch.object(live, "offered", ["a", "b"]), patch.object(live, "PUBLIC", True), \
             patch.object(live, "decode", return_value=np.zeros(16000, dtype=np.float32)), \
             patch.object(live, "transcribe_models", return_value={"a": ("private alpha", 1.2),
                                                                    "b": ("private beta", 2.3)}) as run, \
             contextlib.redirect_stdout(stdout):
            handler.do_POST()
        self.assertEqual(responses[0][0], 200)
        result = responses[0][1]
        self.assertEqual(result["text"], "private alpha")
        self.assertEqual(result["also"], {"model": "b", "text": "private beta", "compute_seconds": 2.3})
        self.assertEqual(run.call_args.args[1], ["a", "b"])
        self.assertNotIn("private", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
