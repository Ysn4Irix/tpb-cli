import pytest
from tpb.interactive import is_back, sanitize_filename


def test_is_back_truthy():
    assert is_back(None) is True
    assert is_back("b") is True
    assert is_back("B") is True
    assert is_back("back") is True
    assert is_back("Back") is True
    assert is_back(":b") is True
    assert is_back("  b  ") is True
    assert is_back("q") is True
    assert is_back("quit") is True


def test_is_back_falsy():
    assert is_back("Severance") is False
    assert is_back("Breaking Bad") is False
    assert is_back("1080p") is False
    assert is_back("1") is False


def test_sanitize_filename():
    assert sanitize_filename("Breaking Bad") == "breaking_bad"
    assert sanitize_filename("Avatar: The Last Airbender!") == "avatar_the_last_airbender"
    assert sanitize_filename("") == "torrents"


def test_tv_flow_instant_back_navigation():
    from unittest.mock import patch, MagicMock
    from tpb.interactive import InteractiveSession
    from tpb.models import Torrent
    from tpb.parser import enrich_torrent_metadata

    mock_client = MagicMock()
    mock_client._cache = {}
    mock_torrent = Torrent(
        id="1",
        name="Severance.S01E01.1080p.mkv",
        info_hash="a" * 40,
        leechers=5,
        seeders=50,
        size_bytes=1000000,
        username="test",
        added=0,
        status="vip",
        category="208",
        imdb="",
    )
    mock_torrent = enrich_torrent_metadata(mock_torrent)
    mock_client.search.return_value = [mock_torrent]

    sess = InteractiveSession(client=mock_client)

    with patch("InquirerPy.inquirer.text") as mock_text, \
         patch("InquirerPy.inquirer.select") as mock_select, \
         patch("InquirerPy.inquirer.checkbox") as mock_checkbox:

        # Step 1: 'Severance', Step 2: '1', then on back from step 2 to step 1: 'b', then step 1: 'b'
        t_mock = MagicMock()
        t_mock.execute.side_effect = ["Severance", "1", "b", "b"]
        mock_text.return_value = t_mock

        # Step 3: '1080p', Step 9 (Export): 'back', on returning to Step 3: 'back'
        s_mock = MagicMock()
        s_mock.execute.side_effect = ["1080p", "back", "back"]
        mock_select.return_value = s_mock

        # Step 6: returns [mock_torrent] -> goes to Step 9
        # Step 9 user selects 'back' -> goes back to Step 6
        # Step 6 user selects 'back' (None) -> goes back to Step 3
        cb_mock = MagicMock()
        cb_mock.execute.side_effect = [[mock_torrent], None]
        mock_checkbox.return_value = cb_mock

        sess.handle_tv_flow()
        # Verifies that navigation returned cleanly without infinite loops or errors


def test_movie_flow_instant_back_navigation():
    from unittest.mock import patch, MagicMock
    from tpb.interactive import InteractiveSession
    from tpb.models import Torrent

    mock_client = MagicMock()
    mock_client._cache = {}
    mock_torrent = Torrent(
        id="2",
        name="Inception.2010.1080p.mkv",
        info_hash="b" * 40,
        leechers=10,
        seeders=100,
        size_bytes=2000000,
        username="test",
        added=0,
        status="vip",
        category="207",
        imdb="",
    )
    mock_client.search.return_value = [mock_torrent]

    sess = InteractiveSession(client=mock_client)

    with patch("InquirerPy.inquirer.text") as mock_text, \
         patch("InquirerPy.inquirer.select") as mock_select, \
         patch("InquirerPy.inquirer.checkbox") as mock_checkbox:

        t_mock = MagicMock()
        t_mock.execute.side_effect = ["Inception", "b"]
        mock_text.return_value = t_mock

        s_mock = MagicMock()
        s_mock.execute.side_effect = ["back"]
        mock_select.return_value = s_mock

        cb_mock = MagicMock()
        cb_mock.execute.side_effect = [[mock_torrent], None]
        mock_checkbox.return_value = cb_mock

        sess.handle_movie_flow()

