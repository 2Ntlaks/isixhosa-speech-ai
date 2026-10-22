"""Make the in-browser (transformers.js 3.0.2) copy of a whisper model: ONNX export + 8-bit weights. R-0017's recipe.

  .venv-onnx2/Scripts/python src/export_onnx.py --model data/models/R-0027 --out data/onnx/R-0027

Run in .venv-onnx2 (transformers 4.41.2, optimum 1.20.0, onnxruntime): newer exports add a `cache_position` decoder
input that transformers.js 3.0.2 does not send (P-0015). Steps:
1. optimum export, task automatic-speech-recognition-with-past (encoder_model, decoder_model_merged, ...).
2. The output layer reuses the word-embedding table through a Transpose node, which dynamic quantisation skips, so a
   full-precision copy of the table (~159 MB for small) would stay. Store the transposed table as its own weight
   (`..._T`) and point the logits MatMul at it, in both branches of the merged decoder (P-0015).
3. quantize_dynamic, QUInt8, MatMul + Gather, subgraphs included -> encoder_model_quantized.onnx,
   decoder_model_merged_quantized.onnx (the two files the demo loads).
"""
import argparse
import os

import numpy as np
import onnx
from onnx import numpy_helper
from onnxruntime.quantization import QuantType, quantize_dynamic
from optimum.exporters.onnx import main_export


def untie_output_layer(path):
    m = onnx.load(path)
    g = m.graph
    inits = {i.name: i for i in g.initializer}
    changed = 0
    for node in g.node:
        for attr in node.attribute:
            sub = attr.g
            if not sub.node:
                continue
            for t in [n for n in sub.node if n.op_type == "Transpose" and n.input[0] in inits]:
                src = t.input[0]
                name = src + "_T"
                if name not in inits:
                    w = numpy_helper.to_array(inits[src])
                    g.initializer.append(numpy_helper.from_array(np.ascontiguousarray(w.T), name))
                    inits[name] = g.initializer[-1]
                for n in sub.node:
                    n.input[:] = [name if x == t.output[0] else x for x in n.input]
                sub.node.remove(t)
                changed += 1
    assert changed == 2, f"expected the tied Transpose in both decoder branches, found {changed}"
    onnx.save(m, path)
    return changed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main_export(a.model, a.out, task="automatic-speech-recognition-with-past")
    dec = os.path.join(a.out, "decoder_model_merged.onnx")
    print("untied output layer in", untie_output_layer(dec), "branches", flush=True)
    for name in ("encoder_model", "decoder_model_merged"):
        quantize_dynamic(os.path.join(a.out, name + ".onnx"), os.path.join(a.out, name + "_quantized.onnx"),
                         weight_type=QuantType.QUInt8, op_types_to_quantize=["MatMul", "Gather"],
                         extra_options={"EnableSubgraph": True})
    for f in sorted(os.listdir(a.out)):
        if f.endswith(".onnx"):
            print(f"{os.path.getsize(os.path.join(a.out, f)) / 1e6:8.1f} MB  {f}")
