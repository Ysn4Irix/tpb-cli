"""Background QThreadPool workers and stale-request orchestration for Apibay queries."""

import logging
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from tpb.api import ApibayClient, ApibayError, CAT_ALL, CAT_MOVIES_HD, CAT_TV_HD
from tpb.models import Torrent, TorrentFile

logger = logging.getLogger(__name__)


def execute_search(client: ApibayClient, query: str, mode: str) -> list[Torrent]:
    """
    Execute an Apibay search matching CLI category fallback semantics.
    - tv: searches HD TV first, then unscoped query if empty
    - movie: searches HD Movies first, then unscoped query if empty
    - general: searches all categories
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    if mode == "tv":
        results = client.search(clean_query, category=CAT_TV_HD)
        if not results:
            results = client.search(clean_query)
        return results

    if mode == "movie":
        results = client.search(clean_query, category=CAT_MOVIES_HD)
        if not results:
            results = client.search(clean_query)
        return results

    return client.search(clean_query, category=CAT_ALL)


def execute_files_lookup(client: ApibayClient, torrent_id: str) -> list[TorrentFile]:
    """Retrieve normalized file-list entries for a torrent ID."""
    return client.get_parsed_files(torrent_id)


class WorkerSignals(QObject):
    """Signals emitted by runnable workers onto the Qt main thread."""

    finished = Signal(int, object)
    error = Signal(int, str)


class SearchWorker(QRunnable):
    """Runs Apibay search off the UI thread."""

    def __init__(self, client: ApibayClient, request_id: int, query: str, mode: str):
        super().__init__()
        self.client = client
        self.request_id = request_id
        self.query = query
        self.mode = mode
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            results = execute_search(self.client, self.query, self.mode)
            self.signals.finished.emit(self.request_id, results)
        except ApibayError as exc:
            self.signals.error.emit(self.request_id, str(exc))
        except Exception:  # pragma: no cover - defensive guard
            logger.exception("Unexpected failure while searching Apibay")
            self.signals.error.emit(self.request_id, "Unexpected search error. Please try again.")


class FilesWorker(QRunnable):
    """Runs torrent file-list fetch off the UI thread."""

    def __init__(self, client: ApibayClient, request_id: int, torrent_id: str):
        super().__init__()
        self.client = client
        self.request_id = request_id
        self.torrent_id = torrent_id
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            files = execute_files_lookup(self.client, self.torrent_id)
            self.signals.finished.emit(self.request_id, files)
        except ApibayError as exc:
            self.signals.error.emit(self.request_id, str(exc))
        except Exception:  # pragma: no cover - defensive guard
            logger.exception("Unexpected failure while fetching torrent files")
            self.signals.error.emit(
                self.request_id, "Unexpected file lookup error. Please try again."
            )


class WorkerManager(QObject):
    """Coordinates background workers and discards stale out-of-order responses."""

    search_started = Signal(str, str)
    search_completed = Signal(str, str, list)
    search_failed = Signal(str)
    search_cancelled = Signal()

    files_started = Signal(str)
    files_completed = Signal(str, list)
    files_failed = Signal(str, str)

    def __init__(self, client: ApibayClient, thread_pool: QThreadPool | None = None):
        super().__init__()
        self.client = client
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._search_seq = 0
        self._files_seq = 0
        self._search_in_flight = False
        self._active_runnables: set[QRunnable] = set()

    @property
    def is_searching(self) -> bool:
        """Return True while an active search has not yet completed or been cancelled."""
        return self._search_in_flight

    def start_search(self, query: str, mode: str) -> int:
        """Schedule a background search request and return its monotonic ID."""
        self._search_seq += 1
        req_id = self._search_seq
        self._search_in_flight = True
        worker = SearchWorker(self.client, req_id, query, mode)
        self._active_runnables.add(worker)

        worker.signals.finished.connect(
            lambda rid, res, q=query, m=mode, w=worker: self._on_search_finished(rid, res, q, m, w)
        )
        worker.signals.error.connect(lambda rid, msg, w=worker: self._on_search_error(rid, msg, w))

        self.search_started.emit(query, mode)
        self.thread_pool.start(worker)
        return req_id

    def cancel_search(self) -> bool:
        """Cancel the current search logically by invalidating its request ID."""
        if not self._search_in_flight:
            return False
        self._search_seq += 1
        self._search_in_flight = False
        self.search_cancelled.emit()
        return True

    def start_files_lookup(self, torrent_id: str) -> int:
        """Schedule a background file-list lookup for a torrent ID."""
        self._files_seq += 1
        req_id = self._files_seq
        worker = FilesWorker(self.client, req_id, torrent_id)
        self._active_runnables.add(worker)

        worker.signals.finished.connect(
            lambda rid, files, tid=torrent_id, w=worker: self._on_files_finished(rid, tid, files, w)
        )
        worker.signals.error.connect(
            lambda rid, msg, tid=torrent_id, w=worker: self._on_files_error(rid, tid, msg, w)
        )

        self.files_started.emit(torrent_id)
        self.thread_pool.start(worker)
        return req_id

    def _on_search_finished(
        self, req_id: int, results: list, query: str, mode: str, worker: QRunnable
    ) -> None:
        self._active_runnables.discard(worker)
        if req_id != self._search_seq:
            return
        self._search_in_flight = False
        self.search_completed.emit(query, mode, results)

    def _on_search_error(self, req_id: int, message: str, worker: QRunnable) -> None:
        self._active_runnables.discard(worker)
        if req_id != self._search_seq:
            return
        self._search_in_flight = False
        self.search_failed.emit(message)

    def _on_files_finished(
        self, req_id: int, torrent_id: str, files: list, worker: QRunnable
    ) -> None:
        self._active_runnables.discard(worker)
        if req_id != self._files_seq:
            return
        self.files_completed.emit(torrent_id, files)

    def _on_files_error(
        self, req_id: int, torrent_id: str, message: str, worker: QRunnable
    ) -> None:
        self._active_runnables.discard(worker)
        if req_id != self._files_seq:
            return
        self.files_failed.emit(torrent_id, message)
