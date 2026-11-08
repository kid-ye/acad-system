"""Parity check: ONNX query vectors must match sentence-transformers.

The corpus embeddings.npy was built with sentence-transformers, so the ONNX
query encoder has to reproduce those vectors or search quality changes. This
gates the cutover: run it after export_onnx.py, require cosine >= 0.999.

    pip install "optimum[onnxruntime]" sentence-transformers
    python scripts/verify_onnx.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import QUERY_PREFIX, ONNX_DIR, EMB_MODEL  # noqa: E402

SAMPLES = [
    "laplace transform",
    "deadlock prevention in operating systems",
    "beam deflection 10 marks",
    "what repeats in thermodynamics",
    "breakpoint chlorination",
    "fourier series",
    "normalization in dbms",
    "op-amp integrator circuit",
]
THRESHOLD = 0.999


def _onnx_encode():
    import onnxruntime as ort
    from tokenizers import Tokenizer

    sess = ort.InferenceSession(str(ONNX_DIR / "model.onnx"),
                                providers=["CPUExecutionProvider"])
    tok = Tokenizer.from_file(str(ONNX_DIR / "tokenizer.json"))
    tok.enable_truncation(max_length=512)
    want = {i.name for i in sess.get_inputs()}

    def enc(text):
        e = tok.encode(text)
        ids = np.asarray([e.ids], dtype=np.int64)
        feed = {"input_ids": ids,
                "attention_mask": np.asarray([e.attention_mask], dtype=np.int64)}
        if "token_type_ids" in want:
            feed["token_type_ids"] = np.zeros_like(ids)
        v = sess.run(None, feed)[0][0, 0].astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-12)

    return enc


def main():
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(EMB_MODEL, device="cpu")
    onnx = _onnx_encode()

    worst = 1.0
    for q in SAMPLES:
        text = QUERY_PREFIX + q
        a = st.encode([text], normalize_embeddings=True,
                      convert_to_numpy=True)[0].astype(np.float32)
        b = onnx(text)
        cos = float(a @ b)                 # both unit-norm
        worst = min(worst, cos)
        flag = "ok" if cos >= THRESHOLD else "FAIL"
        print(f"  {cos:.6f}  {flag}  {q}")

    print(f"worst cosine: {worst:.6f}  (threshold {THRESHOLD})")
    if worst < THRESHOLD:
        print("PARITY FAILED - do not cut over to ONNX")
        sys.exit(1)
    print("PARITY OK")


if __name__ == "__main__":
    main()
