"""Tests for the prompt builder."""

import os
import pytest

from logdiag.diagnosis.golden_path_loader import GoldenPathLoader
from logdiag.diagnosis.prompt_builder import PromptBuilder

GOLDEN_PATH_FILE = os.path.join(
    os.path.dirname(__file__), "..", "config", "golden_paths.yaml"
)


@pytest.fixture
def builder():
    loader = GoldenPathLoader(GOLDEN_PATH_FILE)
    return PromptBuilder(loader)


def test_system_prompt_contains_role(builder):
    prompt = builder.build_system_prompt()
    assert "AUMOBO" in prompt
    assert "log 診斷助手" in prompt


def test_system_prompt_contains_safety_constraints(builder):
    prompt = builder.build_system_prompt()
    assert "只能讀取 log" in prompt
    assert "query_parser_log" in prompt


def test_system_prompt_contains_golden_paths(builder):
    prompt = builder.build_system_prompt()
    assert "localization_start" in prompt
    assert "slam_build" in prompt


def test_system_prompt_contains_output_format(builder):
    prompt = builder.build_system_prompt()
    assert "問題摘要" in prompt
    assert "異常時間線" in prompt
    assert "根因分析" in prompt


def test_build_user_message(builder):
    msg = builder.build_user_message("SLAM 建圖失敗了")
    assert msg["role"] == "user"
    assert msg["content"] == "SLAM 建圖失敗了"
