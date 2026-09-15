"""Unit tests for skill_engine._frontmatter."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine._frontmatter import parse_yaml_frontmatter


def test_parse_yaml_frontmatter_standard():
    content = """---
name: my-skill
description: A wonderful skill for testing
version: 1.0.0
---

# My Skill Documentation
Body content here.
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        f.write(content)
        f_path = f.name

    try:
        data = parse_yaml_frontmatter(f_path)
        assert data["name"] == "my-skill"
        assert data["description"] == "A wonderful skill for testing"
        assert data["version"] == "1.0.0"
    finally:
        os.unlink(f_path)


def test_parse_yaml_frontmatter_multiline_and_blockquote():
    content = """---
name: quote-skill
description: >
  This is a multiline description
  that spans multiple lines.
---
Body
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        f.write(content)
        f_path = f.name

    try:
        data = parse_yaml_frontmatter(f_path)
        assert data["name"] == "quote-skill"
        assert "This is a multiline description" in data["description"]
        assert not data["description"].startswith(">")
    finally:
        os.unlink(f_path)


def test_parse_yaml_frontmatter_nonexistent():
    assert parse_yaml_frontmatter("/nonexistent/path/SKILL.md") == {}


def test_parse_yaml_frontmatter_no_frontmatter():
    content = "# Just a markdown file without YAML frontmatter"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        f.write(content)
        f_path = f.name

    try:
        assert parse_yaml_frontmatter(f_path) == {}
    finally:
        os.unlink(f_path)
