import pytest
from unittest.mock import patch, MagicMock
from tpb.api import ApibayClient, ApibayConnectionError
import httpx


def test_api_search_success():
    client = ApibayClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "101",
            "name": "Severance.S01E01.1080p.WEB.H264",
            "info_hash": "AABBCCDDEEFF00112233445566778899AABBCCDD",
            "leechers": "15",
            "seeders": "320",
            "size": "1500000000",
            "username": "SuperUploader",
            "added": "1650000000",
            "status": "vip",
            "category": "208",
            "imdb": "tt11280740",
        }
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = mock_response
        mock_get_client.return_value.__enter__.return_value = mock_ctx

        results = client.search("Severance")
        assert len(results) == 1
        t = results[0]
        assert t.id == "101"
        assert t.seeders == 320
        assert t.season == 1
        assert t.episode == 1
        assert t.quality == "1080p"
        assert t.codec == "x264"
        assert t.is_vip is True


def test_api_empty_dummy_result():
    client = ApibayClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "0",
            "name": "No results returned",
            "info_hash": "0000000000000000000000000000000000000000",
            "leechers": "0",
            "seeders": "0",
            "size": "0",
        }
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = mock_response
        mock_get_client.return_value.__enter__.return_value = mock_ctx

        results = client.search("NonexistentShow123xyz")
        assert results == []


def test_api_connection_error():
    client = ApibayClient()

    with patch.object(client, "_get_client") as mock_get_client:
        mock_ctx = MagicMock()
        mock_ctx.get.side_effect = httpx.ConnectError("Failed to resolve host")
        mock_get_client.return_value.__enter__.return_value = mock_ctx

        with pytest.raises(ApibayConnectionError):
            client.search("AnyQuery")
