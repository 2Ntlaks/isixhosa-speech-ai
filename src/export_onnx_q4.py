"""Make 4-bit browser copies of a whisper model for transformers.js 4.x on WebGPU (R-0038). Companion to export_onnx.py.

  C:\\Users\\ntlak\\venvs\\onnx-med\\Scripts\\python src/export_onnx_q4.py --model data/models/R-0035 \
      --out C:\\Users\\ntlak\\isixhosa-speech-ai-data\\onnx\\R-0035 --build q4f16 fp16

Run in a venv with transformers 4.41.2 + optimum 1.20.0 (no `cache_position` decoder input, P-0015), onnxruntime
1.27.0, onnx-ir, onnxslim (for src/tjs_float16.py). Steps:
1. optimum export (skipped if the fp32 files are already there), task automatic-speech-recognition-with-past, without
   optimum's merge step: medium's merged fp32 decoder is over protobuf's 2 GB limit ("Failed to serialize proto"), so the
   two decoder halves (decoder_model, decoder_with_past_model) are quantised first and merged after (R-0038).
2. --build, any of:
   q4     MatMul weights to 4 bits (MatMulNBits, block 32, symmetric, accuracy level unset: transformers.js 3.8.1 scripts/quantize.py defaults)
   q4f16  q4, then everything else to float16, inputs/outputs kept float32
   fp16   the whole model in float16, inputs/outputs kept float32
   Files: encoder_model_<kind>.onnx, decoder_model_merged_<kind>.onnx (transformers.js's names).
"""
import argparse
import os

import onnx
import tjs_float16 as float16  # transformers.js 3.8.1's converter (handles If subgraphs, R-0038)
from onnxruntime.quantization.matmul_nbits_quantizer import MatMulNBitsQuantizer

FP32 = ("encoder_model", "decoder_model", "decoder_with_past_model")


def q4(model):
    # accuracy_level left unset as transformers.js does (default None); 4 gave NaN with float16 on CPU (R-0038)
    qz = MatMulNBitsQuantizer(model, bits=4, block_size=32, is_symmetric=True)
    qz.process()
    return qz.model.model


def fp16(model):  # as transformers.js scripts/quantize.py quantize_fp16
    return float16.convert_float_to_float16(model, keep_io_types=True,
                                            disable_shape_infer=model.ByteSize() >= onnx.checker.MAXIMUM_PROTOBUF,
                                            op_block_list=set(float16.DEFAULT_OP_BLOCK_LIST))


def save(model, path):
    big = model.ByteSize() > 1.9e9
    if os.path.exists(path + "_data"):
        os.remove(path + "_data")
    onnx.save(model, path, save_as_external_data=big, all_tensors_to_one_file=True,
              location=os.path.basename(path) + "_data" if big else None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--build", nargs="+", default=["q4f16"], choices=["q4", "q4f16", "fp16"])
    a = ap.parse_args()
    if not all(os.path.exists(os.path.join(a.out, n + ".onnx")) for n in FP32):
        from optimum.exporters.onnx import main_export
        main_export(a.model, a.out, task="automatic-speech-recognition-with-past", no_post_process=True)
    for n in FP32[1:]:
        inputs = [i.name for i in onnx.load(os.path.join(a.out, n + ".onnx"), load_external_data=False).graph.input]
        assert "cache_position" not in inputs, f"{n} has cache_position (P-0015): {inputs}"
    print("decoder inputs: no cache_position", flush=True)
    for kind in a.build:
        dst = os.path.join(a.out, f"encoder_model_{kind}.onnx")
        if not os.path.exists(dst):
            m = onnx.load(os.path.join(a.out, "encoder_model.onnx"))
            save({"q4": q4, "q4f16": lambda x: fp16(q4(x)), "fp16": fp16}[kind](m), dst)
            del m
            print(f"built {dst}", flush=True)
        dst = os.path.join(a.out, f"decoder_model_merged_{kind}.onnx")
        if kind == "fp16" or os.path.exists(dst):
            continue  # an fp16 decoder is not a candidate (B uses the q4f16 decoder)
        from optimum.onnx.graph_transformations import merge_decoders
        halves = [q4(onnx.load(os.path.join(a.out, n + ".onnx"))) for n in FP32[1:]]
        merged = merge_decoders(*halves, strict=False)  # as optimum does: constant encoder outputs added to the past half
        del halves
        save(fp16(merged) if kind == "q4f16" else merged, dst)
        del merged
        print(f"built {dst}", flush=True)
    for f in sorted(os.listdir(a.out)):
        if f.endswith(".onnx") or f.endswith("_data"):
            print(f"{os.path.getsize(os.path.join(a.out, f)) / 1e6:9.2f} MB  {f}")
