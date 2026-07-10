#!/usr/bin/env python3
import os
import sys
import re

def main():
    if len(sys.argv) < 2:
        print("Usage: preview_skill.py <skill_name>")
        sys.exit(1)

    skill = sys.argv[1]
    # Path to SKILL.md
    path = os.path.expanduser(f"~/.agents/skills/{skill}/SKILL.md")

    if not os.path.exists(path):
        print(f"\033[1;31mError: SKILL.md not found for skill '{skill}'\033[0m")
        print(f"Path searched: {path}")
        sys.exit(0)

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"\033[1;31mError reading file: {e}\033[0m")
        sys.exit(0)

    # Match YAML frontmatter
    # A standard frontmatter is enclosed by --- at the very start of the file
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        frontmatter = m.group(1)
        body = content[m.end():]

        # Parse simple YAML (name and description)
        data = {}
        current_key = None
        for line in frontmatter.split("\n"):
            if not line.strip():
                continue
            # If line is indented, it's a continuation of the previous key (e.g. description multi-line string)
            if line.startswith(" ") or line.startswith("\t"):
                if current_key:
                    # Append line, replacing YAML fold markers if present
                    val = line.strip()
                    if val.startswith("-"):
                        data[current_key] += "\n" + val
                    else:
                        data[current_key] += " " + val
            else:
                if ":" in line:
                    key, val = line.split(":", 1)
                    current_key = key.strip()
                    data[current_key] = val.strip()

        name = data.get("name", skill)
        # Format the description nicely
        desc = data.get("description", "")
        # Clean up multi-line formatting issues from YAML like '> ' or '>'
        if desc.startswith(">"):
            desc = desc[1:]
        desc = desc.replace("\n> ", "\n").replace("\n>", "\n")
        desc_lines = [l.strip() for l in desc.split("\n") if l.strip()]

        # Print layout
        print("\033[1;36m" + "=" * 55 + "\033[0m")
        print(f"\033[1;32m Skill: \033[1;37m{name}\033[0m")
        print("\033[1;36m" + "=" * 55 + "\033[0m")
        
        if desc_lines:
            print("\033[1;33mDescription:\033[0m")
            for line in desc_lines:
                print(f"  {line}")
            print("\033[1;36m" + "-" * 55 + "\033[0m")

        print("\033[1;34mContent Preview:\033[0m")
        # Print up to 25 lines of the body content
        body_lines = body.strip().split("\n")
        printed_lines = 0
        for line in body_lines:
            if printed_lines >= 25:
                break
            print(f"  {line}")
            printed_lines += 1
        if len(body_lines) > 25:
            print("\033[1;30m  ... (more content below) ...\033[0m")
    else:
        # No frontmatter, just print the raw file up to 30 lines
        print("\033[1;36m" + "=" * 55 + "\033[0m")
        print(f"\033[1;32m Skill: \033[1;37m{skill}\033[0m")
        print("\033[1;36m" + "=" * 55 + "\033[0m")
        lines = content.strip().split("\n")
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print("\033[1;30m  ... (more content below) ...\033[0m")

if __name__ == "__main__":
    main()
