#!/usr/bin/env python3
"""
Build REPORT.md from modular parts in docs/parts/.

Usage:
    python scripts/build_report.py

Output:
    docs/REPORT.md
"""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
PARTS_DIR = PROJECT_ROOT / "docs" / "parts"
OUTPUT_FILE = PROJECT_ROOT / "docs" / "REPORT.md"

# Order of parts to concatenate
PARTS_ORDER = [
    "00_header.md",
    "01_introduction.md",
    "02_experimental_design.md",
    "03_metrics.md",
    "04_results.md",
    "05_discussion.md",
    "06_threats_to_validity.md",
    "07_conclusion.md",
    "08_footer.md",
]


def build_report():
    """Concatenate all parts into REPORT.md."""

    print(f"Building REPORT.md from parts in {PARTS_DIR}...")

    # Read and concatenate
    content_parts = []
    for part in PARTS_ORDER:
        part_path = PARTS_DIR / part
        with open(part_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Fix image paths: ./figures/ -> figures/ (for REPORT.md context)
        content = content.replace('(../figures/', '(figures/')

        content_parts.append(content)
        content_parts.append("\n")  # Single blank line between all parts

        print(f"  ✓ Added {part}")

    # Write output
    full_content = "".join(content_parts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_content)

    print(f"\n✅ REPORT.md built successfully: {OUTPUT_FILE}")
    print(f"   Total size: {len(full_content):,} characters")

    return True


if __name__ == "__main__":
    success = build_report()
    exit(0 if success else 1)
