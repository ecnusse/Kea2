#!/usr/bin/env python3
"""Verify the built-in rtree produces the same ``covered`` results as the
external ``rtree`` (libspatialindex) package on a UI hierarchy XML.

It runs Kea2's ``_HindenWidgetFilter`` twice on fresh parses of the same XML --
once using the in-tree pure-Python rtree (``kea2.rtree``) and once using the
external ``rtree`` package (if installed) -- and compares the ``covered``
attribute of every node.

Usage::

    python scripts/verify_rtree_covered.py
    python scripts/verify_rtree_covered.py tests/hidden_widget_test.xml
    python scripts/verify_rtree_covered.py tests/hidden_widget_test.xml tests/hidden_widget_result.xml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_filter(xml_path: Path, rtree_module) -> list[tuple[str, str]]:
    """Parse ``xml_path``, run the widget filter, return (bounds, covered) pairs."""
    from lxml import etree

    import kea2.u2Driver as ud

    tree = etree.parse(xml_path)
    root = tree.getroot()

    original = ud.rtree
    ud.rtree = rtree_module
    try:
        ud._HindenWidgetFilter(root)
    finally:
        ud.rtree = original

    return [(e.get("bounds"), e.get("covered")) for e in root.iter("node")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "xml",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1] / "tests" / "hidden_widget_test.xml"),
        help="path to the UI hierarchy XML (default: tests/hidden_widget_test.xml)",
    )
    parser.add_argument(
        "expected",
        nargs="?",
        default=None,
        help="optional expected-result XML to compare against",
    )
    args = parser.parse_args()

    xml_path = Path(args.xml)
    if not xml_path.exists():
        print(f"error: file not found: {xml_path}", file=sys.stderr)
        return 2

    from kea2 import rtree as builtin_rtree

    try:
        import rtree as external_rtree
    except ImportError:
        print("external 'rtree' package is not installed; skipping the comparison.")
        external_rtree = None

    builtin_results = run_filter(xml_path, builtin_rtree)
    print(f"built-in rtree  : {sum(1 for _, c in builtin_results if c == 'true')} nodes marked covered")

    if external_rtree is not None:
        external_results = run_filter(xml_path, external_rtree)
        print(f"external rtree  : {sum(1 for _, c in external_results if c == 'true')} nodes marked covered")

        if builtin_results == external_results:
            print(f"MATCH: built-in and external rtree agree on all {len(builtin_results)} nodes.")
            matched = True
        else:
            matched = False
            print(f"DIFF: built-in and external rtree disagree on "
                  f"{sum(1 for a, b in zip(builtin_results, external_results) if a != b)} nodes:")
            for i, (a, b) in enumerate(zip(builtin_results, external_results)):
                if a != b:
                    print(f"  node #{i}: built-in {a}  external {b}")
    else:
        matched = None

    if args.expected:
        expected_path = Path(args.expected)
        if not expected_path.exists():
            print(f"error: expected file not found: {expected_path}", file=sys.stderr)
            return 2
        from lxml import etree
        expected_results = [(e.get("bounds"), e.get("covered")) for e in etree.parse(expected_path).getroot().iter("node")]
        if builtin_results == expected_results:
            print(f"MATCH: built-in rtree matches expected result on all {len(expected_results)} nodes.")
            expected_matched = True
        else:
            expected_matched = False
            print(f"DIFF: built-in rtree disagrees with {args.expected} on "
                  f"{sum(1 for a, b in zip(builtin_results, expected_results) if a != b)} nodes.")
    else:
        expected_matched = None

    ok = matched is not False and expected_matched is not False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
