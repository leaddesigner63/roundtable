"""Ensure the project root is discoverable on PYTHONPATH when running tools directly."""

from __future__ import annotations

import os
import sys

ROOT_DIR = os.path.dirname(__file__)
if ROOT_DIR and ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
