"""Pytest configuration forcing offscreen Qt rendering for headless test runs."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
