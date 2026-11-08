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
RUN pip install --no-cache-dir -r requirements.txt "huggingface_hub>=0.23"

# Backend code
COPY backend/ backend/

# Read-only data (DBs, embeddings, figures) pulled from the public HF dataset at
# build time. Keeps the build context tiny and self-sufficient: the large files
# no longer need to be present locally. Override HF_DATA_REPO to point elsewhere.
ARG HF_DATA_REPO=kid-ye/acad-data
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('${HF_DATA_REPO}', repo_type='dataset', local_dir='DERIVED_DATA')"

# Exported ONNX query encoder from stage 1 (model.onnx + tokenizer.json)
COPY --from=exporter /onnx DERIVED_DATA/bge-onnx

ENV DERIVED_DATA_DIR=/app/DERIVED_DATA \
    PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
