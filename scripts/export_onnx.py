"""Export the bge-small query encoder to ONNX.

Run once (offline, needs torch + optimum) to produce the files the runtime
loads. The runtime itself needs only onnxruntime + tokenizers, not torch.

    pip install "optimum[onnxruntime]"
    python scripts/export_onnx.py [out_dir]

Default out_dir is DERIVED_DATA/bge-onnx, which config.ONNX_DIR points at. It
writes model.onnx plus the tokenizer files. The corpus embeddings in
embeddings.npy were built with the same model via sentence-transformers, so the
ONNX query vectors must match; scripts/verify_onnx.py checks that.
"""

import sys
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"


def main(out_dir: str) -> None:
    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from transformers import AutoTokenizer

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # export=True traces the HF model to ONNX on first load
    model = ORTModelForFeatureExtraction.from_pretrained(MODEL, export=True)
    model.save_pretrained(out)                       # writes model.onnx + config
    AutoTokenizer.from_pretrained(MODEL).save_pretrained(out)  # tokenizer.json

    print(f"exported {MODEL} -> {out}")
    for f in sorted(out.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    default = repo / "DERIVED_DATA" / "bge-onnx"
    main(sys.argv[1] if len(sys.argv) > 1 else str(default))
