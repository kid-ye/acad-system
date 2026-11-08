"""BMSCE Question Bank API — FastAPI app assembly."""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import semantic
from .config import CORS_ORIGINS
from .db import connection
from .routers import search, meta, questions, files, chat, papers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the embedding matrix and query encoder off the request path. Both are
    # lazy, so without this the first semantic search pays the model load. A
    # daemon thread keeps startup instant and keyword search usable meanwhile.
    threading.Thread(target=semantic.warm, daemon=True,
                     name="semantic-warm").start()
    yield


app = FastAPI(
    title="BMSCE Question Bank API",
    version="2.0",
    description="Keyword + semantic search over BMSCE exam questions.",
    lifespan=lifespan,
)

# No cookies or credentialed requests are used, so keep credentials off; a
# wildcard origin with credentials is rejected by browsers anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Compress responses over ~1KB (search result payloads especially).
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(search.router)
app.include_router(meta.router)
app.include_router(questions.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(papers.router)


@app.get("/api/health")
def health():
    with connection() as con:
        n = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    from . import semantic
    return {"status": "ok", "questions": n, "semantic_loaded": semantic.is_ready()}


@app.get("/api/stats")
def stats():
    with connection() as con:
        def one(q):
            return con.execute(q).fetchone()[0]
        return {
            "questions": one("SELECT COUNT(*) FROM questions"),
            "papers": one("SELECT COUNT(DISTINCT sha) FROM questions"),
            "courses": one("SELECT COUNT(DISTINCT course_code) FROM questions"),
            "branches": one("SELECT COUNT(DISTINCT branch) FROM questions"),
            "topics": one("SELECT COUNT(*) FROM topics"),
            "year_range": list(con.execute(
                "SELECT MIN(year), MAX(year) FROM questions").fetchone()),
        }
