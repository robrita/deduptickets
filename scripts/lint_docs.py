#!/usr/bin/env python3
"""Lint the .rules/ structure and AGENTS.md to enforce structural rules.

Rules enforced:
1. All file paths referenced in AGENTS.md exist
2. AGENTS.md line count ≤ 120
3. Every .md file in .rules/ (top-level) is referenced from AGENTS.md
4. No **CRITICAL** markers in AGENTS.md (they belong in topic docs)

Usage:
    python scripts/lint_docs.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed

Remediation:
    Each error message includes instructions on how to fix it.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"
DOCS_DIR = REPO_ROOT / ".rules"
MAX_AGENTS_LINES = 120


def check_agents_line_count(agents_text: str) -> list[str]:
    """AGENTS.md must not exceed MAX_AGENTS_LINES lines."""
    lines = agents_text.splitlines()
    if len(lines) > MAX_AGENTS_LINES:
        return [
            f"AGENTS.md has {len(lines)} lines (max {MAX_AGENTS_LINES}). "
            f"Move detailed content to a topic doc in .rules/ and keep AGENTS.md as a short map."
        ]
    return []


def check_no_critical_markers(agents_text: str) -> list[str]:
    """AGENTS.md should not contain **CRITICAL** markers — those belong in topic docs."""
    errors: list[str] = []
    for i, line in enumerate(agents_text.splitlines(), 1):
        if "**CRITICAL**" in line:
            errors.append(
                f"AGENTS.md line {i}: Found **CRITICAL** marker. "
                f"Move this rule to the appropriate .rules/ topic file and replace with a one-liner pointer."
            )
    return errors


def check_referenced_files_exist(agents_text: str) -> list[str]:
    """All file paths in AGENTS.md markdown links must exist."""
    errors: list[str] = []
    # Match markdown links like [text](path) but skip http/https URLs
    link_pattern = re.compile(r"\[.*?\]\((?!https?://)(.*?)\)")
    for match in link_pattern.finditer(agents_text):
        ref_path = match.group(1).split("#")[0]  # strip anchors
        if not ref_path:
            continue
        full_path = REPO_ROOT / ref_path
        if not full_path.exists():
            errors.append(
                f"AGENTS.md references '{ref_path}' but file does not exist. "
                f"Create the file or fix the path."
            )
    return errors


def check_orphaned_docs(agents_text: str) -> list[str]:
    """Every top-level .md file in .rules/ must be referenced from AGENTS.md."""
    errors: list[str] = []
    if not DOCS_DIR.is_dir():
        return [
            ".rules/ directory does not exist. "
            "Create it and move detailed rules from AGENTS.md into topic files."
        ]
    for md_file in sorted(DOCS_DIR.glob("*.md")):
        relative = md_file.relative_to(REPO_ROOT).as_posix()
        if relative not in agents_text:
            errors.append(
                f"'{relative}' exists in .rules/ but is not referenced from AGENTS.md. "
                f"Add a pointer in the navigation table or remove the orphaned file."
            )
    return errors


# Sections that are intentionally lists of one-liner pointers, not inline detail.
_WHITELISTED_SECTIONS = {"Critical Rules", "Self-Governance Rules", "Navigation", "Reading Order for New Tasks"}


def check_no_inline_rules(agents_text: str) -> list[str]:
    """Sections in AGENTS.md must not contain more than 2 bullet/numbered items.

    The "map-not-encyclopedia" rule means detailed content belongs in .rules/.
    Sections that are intentionally indexed lists of one-liner pointers are whitelisted.
    """
    errors: list[str] = []
    current_section: str | None = None
    item_count = 0
    section_heading_re = re.compile(r"^##\s+(.+)$")
    item_re = re.compile(r"^\s*[-*]\s|^\s*\d+\.\s")

    for line in agents_text.splitlines():
        heading_match = section_heading_re.match(line)
        if heading_match:
            # Check the section that just ended
            if current_section and current_section not in _WHITELISTED_SECTIONS and item_count > 2:
                errors.append(
                    f"AGENTS.md section '{current_section}' has {item_count} inline items (max 2). "
                    f"Move detailed content to a topic doc in .rules/ and replace with a one-liner pointer."
                )
            current_section = heading_match.group(1).strip()
            item_count = 0
        elif current_section and item_re.match(line):
            item_count += 1

    # Check the last section
    if current_section and current_section not in _WHITELISTED_SECTIONS and item_count > 2:
        errors.append(
            f"AGENTS.md section '{current_section}' has {item_count} inline items (max 2). "
            f"Move detailed content to a topic doc in .rules/ and replace with a one-liner pointer."
        )

    return errors


def main() -> int:
    if not AGENTS_MD.is_file():
        print("ERROR: AGENTS.md not found at repository root.")
        return 1

    agents_text = AGENTS_MD.read_text(encoding="utf-8")

    all_errors: list[str] = []
    all_errors.extend(check_agents_line_count(agents_text))
    all_errors.extend(check_no_critical_markers(agents_text))
    all_errors.extend(check_referenced_files_exist(agents_text))
    all_errors.extend(check_orphaned_docs(agents_text))
    all_errors.extend(check_no_inline_rules(agents_text))

    if all_errors:
        print(f"lint-docs: {len(all_errors)} error(s) found:\n")
        for error in all_errors:
            print(f"  ✗ {error}")
        print(
            "\nRemediation: AGENTS.md should be a short map (~100 lines) pointing to topic docs in .rules/. "
            "Move detailed rules to the appropriate .rules/ file."
        )
        return 1

    print("lint-docs: All checks passed ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
