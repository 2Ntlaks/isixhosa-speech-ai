// Runs the model off the main thread, inside the visitor's browser (transformers.js, ONNX 8-bit, R-0017).
import { pipeline, env } from "./transformers.min.js";  // served from this site so its threads may start (3.0.2)

env.allowLocalModels = false;
env.backends.onnx.wasm.wasmPaths = new URL("./", self.location.href).href;
const MODEL = "Ntlakanipho/whisper-small-isixhosa";
const SR = 16000, CHUNK = 30 * SR;  // Whisper hears 30 s at a time; longer audio goes in 30 s pieces
let asr = null;

async function load() {
  if (!asr) {
    asr = await pipeline("automatic-speech-recognition", MODEL, {
      dtype: { encoder_model: "q8", decoder_model_merged: "q8" },
      device: "wasm",
      progress_callback: p => self.postMessage({ type: "progress", ...p }),
    });
  }
  return asr;
}

self.onmessage = async ({ data }) => {
  try {
    if (data.type === "load") {
      await load();
      self.postMessage({ type: "ready" });
    } else if (data.type === "run") {
      const run = await load(), t = performance.now(), parts = [];
      for (let i = 0; i < data.audio.length; i += CHUNK) {
        // the model borrows Whisper's Swahili tag for isiXhosa (D-0007); it writes isiXhosa
        const out = await run(data.audio.subarray(i, i + CHUNK), { language: "sw", task: "transcribe", max_new_tokens: 225 });
        parts.push(out.text.trim());
      }
      self.postMessage({ type: "result", id: data.id, text: parts.join(" ").trim(), seconds: (performance.now() - t) / 1000 });
    }
  } catch (e) {
    self.postMessage({ type: "error", id: data && data.id, message: String((e && e.message) || e) });
  }
};
