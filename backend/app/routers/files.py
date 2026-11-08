"""Serve the original PDF for a paper and the extracted figure images.

Both resolve paths safely: figures are constrained to FIGURES_DIR/<sha>/, and
PDF paths come from the paper's stored original_paths (repo-relative), verified
to stay under RIPPED_DIR before serving.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from ..config import FIGURES_DIR, PDF_BASE_URL, RIPPED_DIR
from ..db import get_db

router = APIRouter(prefix="/api", tags=["files"])


def _safe_under(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


@router.get("/download/{sha}")
def download_pdf(sha: str, con=Depends(get_db)):
    row = con.execute(
        "SELECT original_paths FROM p.papers WHERE sha = ?", (sha,)).fetchone()
    if not row:
        raise HTTPException(404, "paper not found")
    if PDF_BASE_URL:
        return RedirectResponse(f"{PDF_BASE_URL}/pdfs-{sha[0]}/{sha}.pdf")
    paths = json.loads(row[0]) if row[0] else []
    for rel in paths:
        pdf = RIPPED_DIR / rel
        if _safe_under(RIPPED_DIR, pdf) and pdf.is_file():
            return FileResponse(pdf, media_type="application/pdf",
                                filename=pdf.name)
    raise HTTPException(404, "PDF file not found on disk")


@router.get("/figures/{sha}/{filename}")
def figure(sha: str, filename: str):
    img = FIGURES_DIR / sha / filename
    if not _safe_under(FIGURES_DIR, img) or not img.is_file():
        raise HTTPException(404, "figure not found")
    # Figures are content-addressed by sha, so the bytes at a URL never change.
    # A long immutable cache lets Cloudflare and the browser serve repeats
    # without touching the origin.
    return FileResponse(
        img,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
