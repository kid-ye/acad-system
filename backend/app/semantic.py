"""Semantic search over the precomputed question embeddings.

Loads the float16 matrix (embeddings.npy) and its row-aligned text hashes
(emb_keys.json) once, plus a query encoder. A query -> top (text_hash, score)
pairs; the caller resolves hashes to question rows via the text_hash column and
applies filters.

Two query-encoder backends (config.EMB_BACKEND):
  "onnx" (default) - onnxruntime + tokenizers, no torch. Loads in seconds.
  "st"             - the original sentence-transformers path, kept as a
                     fallback and as the parity reference for the ONNX export.
Both must produce the same vectors, because the corpus in embeddings.npy was
built with the sentence-transformers bge model.
"""

import json
import threading

import numpy as np

from .config import (EMBEDDINGS, EMB_KEYS, EMB_MODEL, QUERY_PREFIX,
                     EMB_BACKEND, ONNX_DIR, EMB_MAX_TOKENS)

_lock = threading.Lock()
_state = {"mat": None, "keys": None, "encode": None}


def _onnx_encoder():
    """Return encode(text)->[384] using onnxruntime + tokenizers (no torch).

    Reproduces bge: CLS-token pooling of the last hidden state, then L2
    normalize. The corpus was built the same way, so the vectors line up.
    """
    import onnxruntime as ort
    from tokenizers import Tokenizer

    sess = ort.InferenceSession(str(ONNX_DIR / "model.onnx"),
                                providers=["CPUExecutionProvider"])
    tok = Tokenizer.from_file(str(ONNX_DIR / "tokenizer.json"))
    tok.enable_truncation(max_length=EMB_MAX_TOKENS)
    want = {i.name for i in sess.get_inputs()}

    def encode(text: str) -> np.ndarray:
        enc = tok.encode(text)
        ids = np.asarray([enc.ids], dtype=np.int64)
        mask = np.asarray([enc.attention_mask], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in want:
            feed["token_type_ids"] = np.zeros_like(ids)
        last_hidden = sess.run(None, feed)[0]          # [1, seq, 384]
        cls = last_hidden[0, 0].astype(np.float32)     # CLS token
        return cls / (np.linalg.norm(cls) + 1e-12)

    return encode


def _st_encoder():
    """Return encode(text)->[384] using sentence-transformers (torch)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMB_MODEL, device="cpu")

    def encode(text: str) -> np.ndarray:
        return model.encode([text], normalize_embeddings=True,
                            convert_to_numpy=True)[0].astype(np.float32)

    return encode


def _ensure():
    if _state["mat"] is not None:
        return
    with _lock:
        if _state["mat"] is not None:
            return
        mat = np.load(EMBEDDINGS).astype(np.float32)   # [N, 384], L2-normalized
        keys = json.loads(EMB_KEYS.read_text(encoding="utf-8"))
        encode = _st_encoder() if EMB_BACKEND == "st" else _onnx_encoder()
        _state.update(mat=mat, keys=keys, encode=encode)


def is_ready():
    return _state["mat"] is not None


def warm():
    _ensure()


def search(query: str, pool: int = 800):
    """Return [(text_hash, score), ...] for the top `pool` nearest questions."""
    _ensure()
    mat, keys, encode = _state["mat"], _state["keys"], _state["encode"]
    qv = encode(QUERY_PREFIX + query)                  # [384], L2-normalized
    scores = mat @ qv
    pool = min(pool, len(scores))
    idx = np.argpartition(-scores, pool - 1)[:pool]
    idx = idx[np.argsort(-scores[idx])]
    return [(keys[i], float(scores[i])) for i in idx]


def search_rows(con, query, filters, select, pool=800):
    """Semantic hits -> filtered question rows, ranked by similarity.

    Returns (rows, {text_hash: score}). Both /api/search/semantic and /api/chat
    need exactly this; keeping one copy stops the two ranking paths drifting.
    """
    hits = search(query, pool=pool)
    if not hits:
        return [], {}
    rank = {h: i for i, (h, _) in enumerate(hits)}
    hashes = list(rank)
    where, params = filters.where("q")
    rows = con.execute(
        f"SELECT {select}, q.text_hash FROM questions q "
        f"WHERE q.text_hash IN ({','.join('?' * len(hashes))}) {where}",
        hashes + params,
    ).fetchall()
    rows.sort(key=lambda r: rank.get(r["text_hash"], 1 << 30))
    return rows, dict(hits)
