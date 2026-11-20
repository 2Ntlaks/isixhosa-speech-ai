// R-0038 browser test worker: R-0035 4-bit (q4f16) on WebGPU with transformers.js 4.3.2, greedy, like the demo's worker.
import { pipeline, env } from "/node_modules/@huggingface/transformers/dist/transformers.min.js";
env.allowRemoteModels = false; env.allowLocalModels = true; env.localModelPath = "/models/";
env.backends.onnx.wasm.wasmPaths = "/node_modules/onnxruntime-web/dist/";
let asr = null;
async function gzipRatio(text) {  // the loop guard's test (Whisper: > 2.4 means repetitive)
  const b = new TextEncoder().encode(text); if (!b.length) return 0;
  const z = await new Response(new Blob([b]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer();
  return b.length / (z.byteLength - 18);  // minus gzip's header and trailer, to match zlib
}
self.onmessage = async ({ data }) => {
  try {
    if (data.type === "load") {
      const t = performance.now();
      asr = await pipeline("automatic-speech-recognition", data.model || "R-0035", {
        dtype: { encoder_model: data.dtype, decoder_model_merged: data.dtype }, device: data.device });
      const load_s = (performance.now() - t) / 1000;
      const t2 = performance.now();
      await asr(new Float32Array(16000), { language: "sw", task: "transcribe", max_new_tokens: 8 });  // shader warm-up
      self.postMessage({ type: "ready", load_s, warmup_s: (performance.now() - t2) / 1000 });
    } else if (data.type === "run") {
      const t = performance.now();
      const out = await asr(data.audio, { language: "sw", task: "transcribe", max_new_tokens: data.max_new_tokens });
      const s = (performance.now() - t) / 1000, text = out.text.trim();
      self.postMessage({ type: "result", text, seconds: s, gzip_ratio: await gzipRatio(text) });
    }
  } catch (e) { self.postMessage({ type: "error", message: String((e && e.stack) || e) }); }
};
