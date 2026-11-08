"""The path-traversal guard for served files (figures, PDFs) must keep every
candidate under its base directory. A hole here serves arbitrary disk files."""

from pathlib import Path

from backend.app.routers.files import _safe_under


def test_allows_a_child_path(tmp_path):
    assert _safe_under(tmp_path, tmp_path / "sha" / "fig.png")


def test_blocks_dotdot_escape(tmp_path):
    base = tmp_path / "figures"
    base.mkdir()
    assert not _safe_under(base, base / ".." / ".." / "secret.txt")


def test_blocks_absolute_path_outside(tmp_path):
    base = tmp_path / "figures"
    base.mkdir()
    assert not _safe_under(base, Path("/etc/passwd"))


def test_base_itself_is_under_base(tmp_path):
    assert _safe_under(tmp_path, tmp_path)


if __name__ == "__main__":  # runnable without pytest
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        b = Path(d)
        assert _safe_under(b, b / "x" / "y.png")
        assert not _safe_under(b, b / ".." / ".." / "secret.txt")
        assert not _safe_under(b, Path("/etc/passwd"))
        assert _safe_under(b, b)
    print("test_files OK")
