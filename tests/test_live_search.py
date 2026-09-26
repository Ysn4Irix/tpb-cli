import pytest
from unittest.mock import MagicMock
from tpb.models import Torrent
from tpb.live_search import LiveSearchSession, get_safe_output


def test_get_safe_output():
    out = get_safe_output()
    assert out is not None


def test_live_search_session_init():
    mock_client = MagicMock()
    session = LiveSearchSession(client=mock_client)
    assert session.results == []
    assert session.selected_index == 0
    assert session.is_searching is False


def test_live_search_perform_search():
    mock_client = MagicMock()
    t1 = Torrent(id="1", name="Test Movie 1080p", info_hash="AAA", leechers=1, seeders=50, size_bytes=1000)
    mock_client.search.return_value = [t1]

    session = LiveSearchSession(client=mock_client)
    session.query_buffer.text = "test"

    session._perform_search("test", "test_")

    assert len(session.results) == 1
    assert session.results[0].name == "Test Movie 1080p"
    assert session.is_searching is False
    assert "test_" in session.cache


def test_live_search_text_changed_and_cache():
    mock_client = MagicMock()
    t1 = Torrent(id="1", name="Cached Movie", info_hash="BBB", leechers=2, seeders=30, size_bytes=2000)
    session = LiveSearchSession(client=mock_client)
    session.cache["matrix_"] = [t1]

    # Buffer with cached text
    session.query_buffer.text = "matrix"
    session._on_text_changed(session.query_buffer)

    assert len(session.results) == 1
    assert session.results[0].name == "Cached Movie"
    # Should not call client since it's cached
    mock_client.search.assert_not_called()


def test_live_search_empty_text():
    mock_client = MagicMock()
    session = LiveSearchSession(client=mock_client)
    session.results = [MagicMock()]
    session.query_buffer.text = ""
    session._on_text_changed(session.query_buffer)

    assert session.results == []
    assert session.is_searching is False
