"""Central paths and settings for the API. No secrets here."""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[2]
# must happen before the getenv calls below: config is imported early (via
# semantic/db), well before llm.py would otherwise load the file
load_dotenv(REPO / ".env")
DERIVED = Path(os.getenv("DERIVED_DATA_DIR") or REPO / "DERIVED_DATA")

QUESTIONS_DB = DERIVED / "questions_v2.db"
PAPERS_DB = DERIVED / "papers_v2.db"
EMBEDDINGS = DERIVED / "embeddings.npy"
EMB_KEYS = DERIVED / "emb_keys.json"

FIGURES_DIR = DERIVED / "figures"          # <sha>/<filename>
# original_paths are stored relative to whichever tree the PDFs were ripped
# into. That tree is ~10k PDFs and is not copied alongside the app, so point
# PAPERS_ROOT at wherever it actually lives; without it /api/download 404s.
RIPPED_DIR = Path(os.getenv("PAPERS_ROOT") or REPO)

# when set, /api/download/{sha} redirects to f"{PDF_BASE_URL}/{sha}.pdf"
# instead of serving from RIPPED_DIR (used in prod, where PDFs live on HF)
PDF_BASE_URL = (os.getenv("PDF_BASE_URL") or "").rstrip("/")

# public URL of this API — prefixed onto figure URLs so <img src=...> in the
# frontend hits the backend directly, not the frontend's own origin
API_BASE_URL = (os.getenv("API_BASE_URL") or "").rstrip("/")

# sentence-transformer used for both the corpus and query embeddings
EMB_MODEL = "BAAI/bge-small-en-v1.5"
# bge-v1.5 is asymmetric: the query (not the corpus) gets this instruction
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Query encoder backend. The corpus embeddings.npy was built with the
# sentence-transformers bge model above; the ONNX export of that same model
# reproduces its query vectors (verified by scripts/export_onnx.py) but loads
# in seconds instead of minutes and drops the torch dependency. "onnx" is the
# default; set EMB_BACKEND=st to fall back to sentence-transformers.
ONNX_DIR = DERIVED / "bge-onnx"            # model.onnx + tokenizer.json live here
EMB_BACKEND = (os.getenv("EMB_BACKEND") or "onnx").lower()
EMB_MAX_TOKENS = 512                        # bge context window

CORS_ORIGINS = (os.getenv("CORS_ORIGINS") or "*").split(",")
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
SEMANTIC_POOL = 800        # top vectors pulled before filtering/pagination
