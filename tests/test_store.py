"""Unit tests for skill_engine._store."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine._store import atomic_save_json, get_zfl_data_dir


def test_atomic_save_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = os.path.join(tmpdir, "subdir", "data.json")
        data = {"hello": "world", "num": 42, "nested": [1, 2, 3]}

        success = atomic_save_json(target_file, data)
        assert success is True
        assert os.path.exists(target_file)

        with open(target_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data


def test_get_zfl_data_dir_xdg_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("XDG_DATA_HOME", tmpdir)
        d = get_zfl_data_dir()
        assert d == os.path.join(tmpdir, "zfl")
        assert os.path.isdir(d)
