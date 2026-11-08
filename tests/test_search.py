"""The FTS query builder must quote every token so punctuation in a user query
cannot break FTS5 syntax (or inject operators)."""

from backend.app.routers.search import _fts_match


def test_quotes_each_token():
    assert _fts_match("deadlock prevention") == '"deadlock" "prevention"'


def test_escapes_embedded_double_quotes():
    # a double quote inside a token is doubled, then the token is quoted
    assert _fts_match('say "hi"') == '"say" """hi"""'


def test_collapses_whitespace_and_drops_empties():
    assert _fts_match("  a   b  ") == '"a" "b"'


def test_empty_query_is_empty_match():
    assert _fts_match("   ") == ""


if __name__ == "__main__":  # runnable without pytest
    assert _fts_match("deadlock prevention") == '"deadlock" "prevention"'
    assert _fts_match('say "hi"') == '"say" """hi"""'
    assert _fts_match("  a   b  ") == '"a" "b"'
    assert _fts_match("   ") == ""
    print("test_search OK")
