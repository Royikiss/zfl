# -*- coding: utf-8 -*-
"""Unit tests for the ZFL Metadata Engine Module."""

import os
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from metadata_engine import (
    FIELD_NAME, FIELD_DESC, FIELD_AUTHOR, FIELD_VERSION, FIELD_DEPS,
    parse_bool, parse_deps, parse_string, validate, compile_cache,
    load, MetadataRecord
)


def test_parse_bool():
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("on") is True
    assert parse_bool("是") is True
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("no") is False
    assert parse_bool("否") is False
    assert parse_bool("invalid", default=True) is True
    assert parse_bool(None, default=False) is False
    assert parse_bool(True) is True


def test_parse_deps():
    assert parse_deps("") == ()
    assert parse_deps(None) == ()
    assert parse_deps("curl jq") == ("curl", "jq")
    assert parse_deps("curl, jq, tar") == ("curl", "jq", "tar")
    assert parse_deps(" git , , python3 ") == ("git", "python3")
    assert parse_deps(["curl", "jq"]) == ("curl", "jq")


def test_parse_string_canonical_fields():
    content = """#? name: test_func
#? description: A sample test function
#? author: Developer
#? version: 2.1.0
#? deps: curl, jq
#? usage: test_func [arg]
#? example: test_func hello
#? protected: true
#? quiet: yes

function test_func() {
    echo "hi"
}
"""
    rec = parse_string(content, filepath="functions/test_func.zsh")
    assert rec.name == "test_func"
    assert rec.description == "A sample test function"
    assert rec.author == "Developer"
    assert rec.version == "2.1.0"
    assert rec.deps == ("curl", "jq")
    assert rec.usage == "test_func [arg]"
    assert rec.example == "test_func hello"
    assert rec.is_protected is True
    assert rec.is_quiet is True


def test_parse_string_chinese_aliases():
    content = """#? 名称: my_tool
#? 描述: 终端测试工具
#? 作者: 张三
#? 版本: 1.0.0
#? 依赖: tar gzip
#? 用法: my_tool <file>
#? 示例: my_tool data.tar
#? 受保护: 是
#? 免提示: 1

my_tool() {
    true
}
"""
    rec = parse_string(content)
    assert rec.name == "my_tool"
    assert rec.description == "终端测试工具"
    assert rec.author == "张三"
    assert rec.version == "1.0.0"
    assert rec.deps == ("tar", "gzip")
    assert rec.usage == "my_tool <file>"
    assert rec.example == "my_tool data.tar"
    assert rec.is_protected is True
    assert rec.is_quiet is True


def test_header_boundary_termination():
    content = """# Header comment
#? name: early_stop
#? description: First desc

echo "code line here"

#? description: Should not be parsed
"""
    rec = parse_string(content)
    assert rec.name == "early_stop"
    assert rec.description == "First desc"


def test_validation_success():
    content = """#? name: valid_tool
#? description: Test description
#? author: Tester
#? version: 1.0.0
#? deps: 
#? usage: valid_tool
#? example: valid_tool
"""
    rec = parse_string(content, filepath="functions/valid_tool.zsh")
    res = validate(rec)
    assert res.is_valid is True
    assert len(res.issues) == 0


def test_validation_missing_fields():
    # Missing deps, usage, example
    content = """#? name: incomplete_tool
#? description: Test description
#? author: Tester
#? version: 1.0.0
"""
    rec = parse_string(content, filepath="functions/incomplete_tool.zsh")
    res = validate(rec)
    assert res.is_valid is False
    assert len(res.warnings) == 1
    assert "deps/依赖" in res.warnings[0].message
    assert "usage/用法" in res.warnings[0].message
    assert "example/示例" in res.warnings[0].message


def test_validation_mismatched_filename():
    content = """#? name: wrong_name
#? description: Test description
#? author: Tester
#? version: 1.0.0
#? deps:
#? usage: wrong_name
#? example: wrong_name
"""
    rec = parse_string(content, filepath="functions/correct_name.zsh")
    res = validate(rec)
    assert res.is_valid is False
    assert len(res.errors) == 1
    assert "不匹配" in res.errors[0].message or "does not match" in res.errors[0].message


def test_compile_cache(tmp_path):
    cache_file = tmp_path / "metadata.zsh"
    out = compile_cache(output_file=cache_file)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "typeset -gA ZFL_META_NAMES" in text
    assert "typeset -gA ZFL_META_DESC" in text
    assert "ZFL_META_NAMES[extract]='extract'" in text
    assert "ZFL_META_PROTECTED[extract]='1'" in text
