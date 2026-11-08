---
title: Pyqheaven Backend
emoji: 📚
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Pyqheaven backend (FastAPI)

Keyword + semantic search API over BMSCE past exam questions. Query embedding
runs on ONNX runtime (no torch); the read-only data (SQLite DBs, embeddings,
figures) is pulled from a HF dataset at build time.

This file is the Space card. Copy it to your Space repo as `README.md` — the
YAML front matter above is what tells HF to build the `Dockerfile` as a Docker
Space on port 7860. See `docs/hf-migration-runbook.md` in the main repo for
setup.
