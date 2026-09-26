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


def test_is_back_falsy():
    assert is_back("Severance") is False
    assert is_back("Breaking Bad") is False
    assert is_back("1080p") is False
    assert is_back("1") is False


def test_sanitize_filename():
    assert sanitize_filename("Breaking Bad") == "breaking_bad"
    assert sanitize_filename("Avatar: The Last Airbender!") == "avatar_the_last_airbender"
    assert sanitize_filename("") == "torrents"
