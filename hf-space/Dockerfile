# Hugging Face Space (Docker SDK) image for the Pyqheaven backend.
# Mirrors the main multi-stage ONNX build, adapted for HF Spaces:
#   - runs as the uid-1000 user HF requires
#   - listens on $PORT (HF injects it; defaults to 7860 locally)
#   - pulls the read-only data (DBs, embeddings, figures) from a HF dataset at
#     build time, so the Space repo itself stays tiny
#
# Copy this file to your Space repo as `Dockerfile`. See
# docs/hf-migration-runbook.md for the full steps.

# --- Stage 1: export the bge query encoder to ONNX (torch stays out of runtime)
FROM python:3.11-slim AS exporter
WORKDIR /build
COPY requirements-export.txt .
RUN pip install --no-cache-dir -r requirements-export.txt
COPY scripts/export_onnx.py scripts/export_onnx.py
RUN python scripts/export_onnx.py /onnx

# --- Stage 2: lean runtime ---------------------------------------------------
FROM python:3.11-slim

# HF runs the container process as uid 1000.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "huggingface_hub>=0.23"

COPY --chown=user backend/ backend/

# Read-only data pulled from a PUBLIC HF dataset you create once (see runbook).
# Edit the default to match the dataset you upload to.
ARG HF_DATA_REPO=kid-ye/acad-data
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('${HF_DATA_REPO}', repo_type='dataset', local_dir='DERIVED_DATA')"

# Exported ONNX encoder from stage 1
COPY --from=exporter --chown=user /onnx DERIVED_DATA/bge-onnx

USER user
ENV DERIVED_DATA_DIR=/home/user/app/DERIVED_DATA \
    PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
