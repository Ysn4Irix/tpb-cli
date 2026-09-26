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

        # Step 1: title 'Severance', then after backing out from Step 3 -> Step 1: 'b'
        t_mock = MagicMock()
        t_mock.execute.side_effect = ["Severance", "b"]
        mock_text.return_value = t_mock

        # Step 3: selects season 1
        # Step 4: selects '1080p'
        # Step 9 (Export): selects 'back' -> returns to Step 6
        # On Step 4 (after back from Step 6): selects 'back' -> returns to Step 3
        # On Step 3: selects 'back' -> returns to Step 1
        s_mock = MagicMock()
        s_mock.execute.side_effect = [1, "1080p", "back", "back", "back"]
        mock_select.return_value = s_mock

        # Step 6: first returns [mock_torrent] -> goes to Step 9
        # Step 6: then on back from Step 9, returns None (back) -> goes to Step 4
        cb_mock = MagicMock()
        cb_mock.execute.side_effect = [[mock_torrent], None]
        mock_checkbox.return_value = cb_mock

        sess.handle_tv_flow()
        # Verifies that navigation returned cleanly without infinite loops or errors


def test_tv_flow_series_disambiguation():
    from unittest.mock import patch, MagicMock
    from tpb.interactive import InteractiveSession
    from tpb.models import Torrent
    from tpb.parser import enrich_torrent_metadata

    mock_client = MagicMock()
    mock_client._cache = {}
    t_us1 = enrich_torrent_metadata(Torrent(id="1", name="The.Office.US.S01E01.1080p", info_hash="1", leechers=1, seeders=10, size_bytes=100))
    t_us2 = enrich_torrent_metadata(Torrent(id="2", name="The.Office.US.S01E02.1080p", info_hash="2", leechers=1, seeders=10, size_bytes=100))
    t_uk1 = enrich_torrent_metadata(Torrent(id="3", name="The.Office.UK.S01E01.720p", info_hash="3", leechers=1, seeders=10, size_bytes=100))
    t_uk2 = enrich_torrent_metadata(Torrent(id="4", name="The.Office.UK.S01E02.720p", info_hash="4", leechers=1, seeders=10, size_bytes=100))
    mock_client.search.return_value = [t_us1, t_us2, t_uk1, t_uk2]

    sess = InteractiveSession(client=mock_client)

    with patch("InquirerPy.inquirer.text") as mock_text, \
         patch("InquirerPy.inquirer.select") as mock_select:

        # Step 1: 'The Office', then on back returns 'b'
        t_mock = MagicMock()
        t_mock.execute.side_effect = ["The Office", "b"]
        mock_text.return_value = t_mock

        # Step 25: Disambiguation choice -> user picks 'back'
        s_mock = MagicMock()
        s_mock.execute.side_effect = ["back"]
        mock_select.return_value = s_mock

        sess.handle_tv_flow()



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

