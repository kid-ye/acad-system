# --- Stage 1: export the bge model to ONNX (needs torch + optimum) ---------
# This heavy toolchain stays out of the final image; only the exported ONNX
# files are copied forward.
FROM python:3.11-slim AS exporter
WORKDIR /build
COPY requirements-export.txt .
RUN pip install --no-cache-dir -r requirements-export.txt
COPY scripts/export_onnx.py scripts/export_onnx.py
RUN python scripts/export_onnx.py /onnx

# --- Stage 2: lean runtime (onnxruntime only, no torch) ---------------------
FROM python:3.11-slim
WORKDIR /app

# Runtime Python deps. All have prebuilt wheels, so no compiler toolchain.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ backend/

# Data files (provided at build; large files are gitignored and mounted/added)
COPY DERIVED_DATA/questions_v2.db DERIVED_DATA/questions_v2.db
COPY DERIVED_DATA/papers_v2.db DERIVED_DATA/papers_v2.db
COPY DERIVED_DATA/embeddings.npy DERIVED_DATA/embeddings.npy
COPY DERIVED_DATA/emb_keys.json DERIVED_DATA/emb_keys.json
COPY DERIVED_DATA/figures/ DERIVED_DATA/figures/

# Exported ONNX query encoder from stage 1 (model.onnx + tokenizer.json)
COPY --from=exporter /onnx DERIVED_DATA/bge-onnx

ENV DERIVED_DATA_DIR=/app/DERIVED_DATA
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
