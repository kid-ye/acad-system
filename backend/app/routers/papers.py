"""Browse and bulk-download the original PDFs.

Selection is by one or more course codes plus a year range. `/papers` lists
what matches (with sizes, so the UI can warn before a large download) and
`/papers/zip` returns them as one archive.
"""

import json
import os
import tempfile
import zipfile
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..config import PDF_BASE_URL, RIPPED_DIR
from ..db import get_db
from .files import _safe_under

router = APIRouter(prefix="/api", tags=["papers"])

# A whole branch-year is a reasonable ask; the entire 7.6 GB corpus is not.
MAX_ZIP_FILES = 300
MAX_ZIP_BYTES = 750 * 1024 * 1024

PCOLS = ("sha", "course_code", "course_name", "year", "exam_type", "semester",
         "branch", "program", "num_pages")


def _pdf_path(original_paths):
    """First stored path that actually exists, or None."""
    for rel in (json.loads(original_paths) if original_paths else []):
        pdf = RIPPED_DIR / rel
        if _safe_under(RIPPED_DIR, pdf) and pdf.is_file():
            return pdf
    return None


def _select(con, codes, year_min, year_max):
    if not codes:
        return []
    marks = ",".join("?" * len(codes))
    sql = (f"SELECT {', '.join(PCOLS)}, original_paths FROM p.papers "
           # a paper can serve several codes, so match the join table too
           f"WHERE (course_code IN ({marks}) OR sha IN "
           f"(SELECT sha FROM p.paper_courses WHERE course_code IN ({marks}))) ")
    params = list(codes) + list(codes)
    if year_min is not None:
        sql += "AND year >= ? "
        params.append(year_min)
    if year_max is not None:
        sql += "AND year <= ? "
        params.append(year_max)
    sql += "ORDER BY course_code, year DESC, exam_type"
    return con.execute(sql, params).fetchall()


def _name(row):
    """Readable, collision-free name inside the archive."""
    bits = [row["course_code"] or "unknown", str(row["year"] or ""),
            (row["exam_type"] or "").replace(" ", "-"), row["sha"][:8]]
    return "_".join(b for b in bits if b) + ".pdf"


@router.get("/papers")
def list_papers(
    course_code: list[str] = Query(default=[]),
    year_min: int | None = None,
    year_max: int | None = None,
    con=Depends(get_db),
):
    out, total = [], 0
    for r in _select(con, course_code, year_min, year_max):
        pdf = _pdf_path(r["original_paths"])
        size = pdf.stat().st_size if pdf else 0
        total += size
        url = (f"{PDF_BASE_URL}/pdfs-{r['sha'][0]}/{r['sha']}.pdf" if PDF_BASE_URL
               else f"/api/download/{r['sha']}")
        out.append({**{c: r[c] for c in PCOLS},
                    "filename": _name(r), "size_bytes": size,
                    "available": pdf is not None or bool(PDF_BASE_URL),
                    "download_url": url})
    return {"count": len(out), "total_bytes": total,
            "max_files": MAX_ZIP_FILES, "max_bytes": MAX_ZIP_BYTES,
            "papers": out}


@router.get("/papers/zip")
def zip_papers(
    course_code: list[str] = Query(default=[]),
    year_min: int | None = None,
    year_max: int | None = None,
    sha: list[str] = Query(default=[]),
    con=Depends(get_db),
):
    # sha[] narrows the selection to a user-picked subset (checkbox flow); the
    # underlying course_code/year_min/year_max still gate what's selectable at
    # all, so a caller can't zip papers outside their permitted courses.
    rows = _select(con, course_code, year_min, year_max)
    if sha:
        wanted = set(sha)
        rows = [r for r in rows if r["sha"] in wanted]
    if not rows:
        raise HTTPException(404, "no PDFs match that selection")
    if len(rows) > MAX_ZIP_FILES:
        raise HTTPException(413, f"{len(rows)} papers exceeds the "
                                 f"{MAX_ZIP_FILES}-file limit; narrow the years")

    # Two sources for the PDF bytes: local disk (dev) or PDF_BASE_URL (prod).
    # Sizes aren't known upfront in prod, so the MAX_ZIP_BYTES check happens
    # opportunistically while writing.
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    written = 0
    # Any failure here (a network error, or the 413 below) must delete the temp
    # file; only the success path hands it to FileResponse's cleanup task.
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_STORED) as z:
            for r in rows:
                name = _name(r)
                if PDF_BASE_URL:
                    url = f"{PDF_BASE_URL}/pdfs-{r['sha'][0]}/{r['sha']}.pdf"
                    # stream the PDF straight into the zip instead of buffering
                    # the whole file in memory
                    with requests.get(url, timeout=30, allow_redirects=True,
                                      stream=True) as resp:
                        if resp.status_code != 200:
                            continue  # skip missing files, don't fail the zip
                        with z.open(name, "w") as dst:
                            for chunk in resp.iter_content(64 * 1024):
                                written += len(chunk)
                                if written > MAX_ZIP_BYTES:
                                    raise HTTPException(413, "exceeded "
                                        f"{MAX_ZIP_BYTES // 1024 // 1024} MB; "
                                        "select fewer papers")
                                dst.write(chunk)
                else:
                    pdf = _pdf_path(r["original_paths"])
                    if pdf:
                        z.write(pdf, name)
    except BaseException:
        os.unlink(tmp.name)
        raise

    label = (course_code[0] if len(course_code) == 1 else f"{len(course_code)}-courses")
    return FileResponse(
        tmp.name, media_type="application/zip",
        filename=f"pyqheaven_{label}.zip",
        background=BackgroundTask(os.unlink, tmp.name),
    )
