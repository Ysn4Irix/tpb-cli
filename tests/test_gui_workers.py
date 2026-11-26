"""Unit tests for background search/files execution and stale-request cancellation."""

from unittest.mock import MagicMock

from tpb.api import ApibayError, CAT_ALL, CAT_MOVIES_HD, CAT_TV_HD
from tpb.gui.workers import WorkerManager, execute_files_lookup, execute_search
from tpb.models import Torrent, TorrentFile


def _make_torrent(tid: str = "1", name: str = "Sample.Release.1080p") -> Torrent:
    return Torrent(
        id=tid,
        name=name,
        info_hash="A" * 40,
        leechers=2,
        seeders=50,
        size_bytes=1024 * 1024 * 500,
    )


def test_execute_search_category_fallbacks():
    client = MagicMock()
    tv_hit = _make_torrent("10", "Severance.S01E01.1080p")
    client.search.side_effect = [[], [tv_hit]]

    # TV tries CAT_TV_HD first, falls back to unscoped query when empty
    res = execute_search(client, "Severance", "tv")
    assert res == [tv_hit]
    assert client.search.call_args_list[0].kwargs == {"category": CAT_TV_HD}
    assert client.search.call_args_list[1].kwargs == {}

    client.reset_mock()
    movie_hit = _make_torrent("20", "Inception.2010.1080p")
    client.search.side_effect = [[movie_hit]]
    res_m = execute_search(client, "Inception", "movie")
    assert res_m == [movie_hit]
    client.search.assert_called_once_with("Inception", category=CAT_MOVIES_HD)

    client.reset_mock()
    client.search.side_effect = [[movie_hit]]
    res_g = execute_search(client, "Linux ISO", "general")
    assert res_g == [movie_hit]
    client.search.assert_called_once_with("Linux ISO", category=CAT_ALL)


def test_execute_files_lookup():
    client = MagicMock()
    expected = [TorrentFile(name="video.mkv", size_bytes=2048)]
    client.get_parsed_files.return_value = expected
    assert execute_files_lookup(client, "99") == expected
    client.get_parsed_files.assert_called_once_with("99")


def test_worker_manager_ignores_stale_responses(qapp):
    pool = MagicMock()
    client = MagicMock()
    manager = WorkerManager(client=client, thread_pool=pool)

    completed_events = []
    failed_events = []
    manager.search_completed.connect(lambda q, m, r: completed_events.append((q, m, r)))
    manager.search_failed.connect(lambda msg: failed_events.append(msg))

    req1 = manager.start_search("First", "tv")
    req2 = manager.start_search("Second", "tv")
    assert req2 > req1

    # Capture queued workers from thread_pool.start
    worker1 = pool.start.call_args_list[0].args[0]
    worker2 = pool.start.call_args_list[1].args[0]

    # Simulate stale req1 finishing AFTER req2 started -> must be ignored
    manager._on_search_finished(req1, [_make_torrent("1")], "First", "tv", worker1)
    assert completed_events == []

    # Active req2 finishes -> emitted cleanly
    t2 = _make_torrent("2", "Second.S01E01")
    manager._on_search_finished(req2, [t2], "Second", "tv", worker2)
    assert len(completed_events) == 1
    assert completed_events[0][0] == "Second"
    assert completed_events[0][2] == [t2]

    # Stale error for req1 should also be dropped if newer request active
    req3 = manager.start_search("Third", "movie")
    assert req3 > req2
    worker3 = pool.start.call_args_list[2].args[0]
    manager._on_search_error(req2, str(ApibayError("old timeout")), worker2)
    assert failed_events == []

    manager._on_search_error(req3, "Connection refused", worker3)
    assert failed_events == ["Connection refused"]


def test_worker_manager_cancel_search(qapp):
    pool = MagicMock()
    client = MagicMock()
    manager = WorkerManager(client=client, thread_pool=pool)

    cancelled_events = []
    completed_events = []
    manager.search_cancelled.connect(lambda: cancelled_events.append(True))
    manager.search_completed.connect(lambda q, m, r: completed_events.append((q, m, r)))

    assert manager.cancel_search() is False
    assert manager.is_searching is False

    req1 = manager.start_search("Breaking Bad", "tv")
    assert manager.is_searching is True
    worker1 = pool.start.call_args_list[0].args[0]

    assert manager.cancel_search() is True
    assert manager.is_searching is False
    assert cancelled_events == [True]

    # Late worker completion after cancel must be discarded
    manager._on_search_finished(req1, [_make_torrent("9")], "Breaking Bad", "tv", worker1)
    assert completed_events == []
