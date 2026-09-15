"""Unit tests for skill_engine._display utilities."""

import os
import sys

# Ensure python/ is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine._display import (
    strip_ansi,
    clean_item_id,
    get_display_width,
    pad_display,
    truncate_display,
    circled_num,
)


def test_strip_ansi():
    assert strip_ansi("\033[1;32mhello\033[0m") == "hello"
    assert strip_ansi("\033[0;90m---\033[0m") == "---"
    assert strip_ansi("plain text") == "plain text"
    assert strip_ansi("") == ""


def test_clean_item_id():
    # Tree prefix stripping
    assert clean_item_id("  ├── prototype") == "prototype"
    assert clean_item_id("  └── nuwa-skill") == "nuwa-skill"
    assert clean_item_id("• my-skill") == "my-skill"
    # Group pattern
    assert clean_item_id("▶ group:startup [极简创业者]") == "group:startup"
    assert clean_item_id("▼ group:dev [日常开发协作]") == "group:dev"
    assert clean_item_id("") == ""
    # With ANSI codes
    assert clean_item_id("\033[1;32m• \033[0;37mfind-community\033[0m") == "find-community"


def test_get_display_width():
    # ASCII characters = 1 visual width
    assert get_display_width("hello") == 5
    # CJK characters (wide/fullwidth) = 2 visual width
    assert get_display_width("你好") == 4
    assert get_display_width("极简创业者 (Startup)") == 20
    # ANSI escape codes should be ignored in width
    assert get_display_width("\033[1;32mhello\033[0m") == 5


def test_pad_display():
    assert pad_display("test", 8) == "test    "
    assert pad_display("你好", 6) == "你好  "
    assert pad_display("test", 8, align="right") == "    test"
    assert pad_display("test", 8, align="center") == "  test  "
    # Already wider than target
    assert pad_display("longer_string", 5) == "longer_string"


def test_truncate_display():
    assert truncate_display("short", 10) == "short"
    # Truncate ASCII
    truncated = truncate_display("very_long_skill_name", 10, suffix="…")
    assert get_display_width(truncated) <= 10
    assert truncated.endswith("…")
    # Truncate CJK without splitting multi-byte characters
    cjk_trunc = truncate_display("这是一个非常长的技能中文名称描述", 10, suffix="…")
    assert get_display_width(cjk_trunc) <= 10
    assert cjk_trunc.endswith("…")


def test_circled_num():
    assert circled_num(1) == "①"
    assert circled_num(10) == "⑩"
    assert circled_num(20) == "⑳"
    assert circled_num(21) == "(21)"
    assert circled_num(0) == "(0)"
