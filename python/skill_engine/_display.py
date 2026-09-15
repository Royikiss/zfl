"""Shared terminal display utilities for the skill engine."""

import os
import re
import sys
import unicodedata

# Language detection
LANG = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
IS_ZH = LANG.startswith("zh")

ANSI_REGEX = re.compile(r'\033\[[0-9;]*[a-zA-Z]')


def strip_ansi(s):
    """Remove ANSI escape codes from a string."""
    return ANSI_REGEX.sub('', s)


def clean_item_id(s):
    """Extract skill or group identifier from FZF-formatted display strings."""
    if not s:
        return ""
    s_clean = strip_ansi(s)
    s_clean = re.sub(r'^[ \t\u2502\u251c\u2514\u2500\-\+\U0001F4E6\U0001F4C1\U0001F4C2\u2022\u25B6\u25BC\s]+', '', s_clean).strip()
    parts = s_clean.split()
    if not parts:
        return ""
    token = parts[0].strip("[](),:;")
    if "group:" in s_clean and not token.startswith("group:"):
        m = re.search(r'group:[^\s\[\]()]+', s_clean)
        if m:
            return m.group(0).strip("[](),:;")
    return token


def get_display_width(s):
    """Calculate the true visual width of a string, accounting for CJK characters."""
    s_clean = strip_ansi(s)
    w = 0
    for ch in s_clean:
        status = unicodedata.east_asian_width(ch)
        if status in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w


def pad_display(s, target_width, align='left'):
    """Pad a string to target visual width with alignment support."""
    curr_w = get_display_width(s)
    pad_len = max(0, target_width - curr_w)
    if align == 'right':
        return " " * pad_len + s
    elif align == 'center':
        left = pad_len // 2
        right = pad_len - left
        return " " * left + s + " " * right
    else:
        return s + " " * pad_len


def truncate_display(s, max_w, suffix="\u2026"):
    """Truncate a string to max visual width, appending suffix."""
    curr_w = get_display_width(s)
    if curr_w <= max_w:
        return s
    suffix_w = get_display_width(suffix)
    target = max_w - suffix_w
    if target <= 0:
        return suffix[:max_w]
    res = []
    w = 0
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
        if w + cw > target:
            break
        res.append(ch)
        w += cw
    return "".join(res) + suffix


def c_print(color_code, msg, file=sys.stdout):
    """Print message with ANSI color codes."""
    if hasattr(file, 'isatty') and file.isatty():
        file.write(f"\033[{color_code}m{msg}\033[0m\n")
    else:
        file.write(f"{msg}\n")
    file.flush()


def circled_num(n):
    """Return a circled number character for n (1-20), else fallback to (n)."""
    if 1 <= n <= 20:
        return chr(0x245F + n)
    return f"({n})"
