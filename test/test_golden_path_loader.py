"""Tests for the Golden Path loader."""

import os
import pytest

from logdiag.diagnosis.golden_path_loader import GoldenPathLoader

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
GOLDEN_PATH_FILE = os.path.join(FIXTURE_DIR, "golden_paths.yaml")


@pytest.fixture
def loader():
    return GoldenPathLoader(GOLDEN_PATH_FILE)


def test_load_path_ids(loader):
    ids = loader.path_ids
    assert "localization_start" in ids
    assert "slam_build" in ids
    assert "sensor_health" in ids
    assert "system_boot" in ids


def test_get_path_localization(loader):
    path = loader.get_path("localization_start")
    assert path is not None
    assert path["trigger"] == "loc:mobile_setting_finish"
    assert len(path["steps"]) == 6
    assert len(path["error_patterns"]) == 2


def test_get_path_steps_have_required_fields(loader):
    for path_id in loader.path_ids:
        path = loader.get_path(path_id)
        for step in path["steps"]:
            assert "pattern" in step
            assert "timeout_ms" in step


def test_get_nonexistent_path(loader):
    assert loader.get_path("nonexistent") is None


def test_format_for_prompt_contains_all_paths(loader):
    prompt_text = loader.format_for_prompt()
    for path_id in loader.path_ids:
        assert path_id in prompt_text


def test_format_for_prompt_contains_on_missing(loader):
    prompt_text = loader.format_for_prompt()
    assert "地圖載入逾時" in prompt_text
    assert "LiDAR brand 配置" in prompt_text
