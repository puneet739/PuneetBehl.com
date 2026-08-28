"""Render the pytest and coverage results into the GitHub Actions run summary.

Reads the JUnit XML pytest writes and the Cobertura XML coverage.py writes, and
appends two Markdown sections to $GITHUB_STEP_SUMMARY. Runs even when the test
step failed, so a red run still explains itself on the summary page.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

JUNIT = Path("junit.xml")
COVERAGE = Path("coverage.xml")


def _suites(root: ET.Element) -> list[ET.Element]:
    return [root] if root.tag == "testsuite" else list(root.iter("testsuite"))


def test_section(out: list[str]) -> None:
    out.append("## Test results\n")
    if not JUNIT.exists():
        out.append("_No JUnit report was produced — the test step did not run._\n")
        return

    suites = _suites(ET.parse(JUNIT).getroot())
    total = sum(int(s.get("tests", 0)) for s in suites)
    failed = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    duration = sum(float(s.get("time", 0)) for s in suites)
    passed = total - failed - errors - skipped

    bad = failed + errors
    headline = (
        f"❌ **{bad} failed**, {passed} passed of {total} in {duration:.2f}s"
        if bad
        else f"✅ **{passed} passed** of {total} in {duration:.2f}s"
    )
    out.append(headline + "\n")
    out.append("| Total | Passed | Failed | Errors | Skipped |")
    out.append("|------:|-------:|-------:|-------:|--------:|")
    out.append(f"| {total} | {passed} | {failed} | {errors} | {skipped} |\n")

    broken = [
        (case, kind)
        for suite in suites
        for case in suite.iter("testcase")
        for kind in ("failure", "error")
        if case.find(kind) is not None
    ]
    if broken:
        out.append("### Failures\n")
        for case, kind in broken:
            name = f"{case.get('classname', '')}::{case.get('name', '')}".lstrip(":")
            message = (case.find(kind).get("message") or "").splitlines()
            first = message[0][:200] if message else kind
            out.append(f"- `{name}` — {first}")
        out.append("")


def coverage_section(out: list[str]) -> None:
    out.append("## Coverage\n")
    if not COVERAGE.exists():
        out.append("_No coverage report was produced._\n")
        return

    root = ET.parse(COVERAGE).getroot()
    # Class filenames are relative to the configured source root, so "app" alone
    # would render as bare "content.py". Put the package prefix back.
    source = root.find("sources/source")
    prefix = f"{Path(source.text.strip()).name}/" if source is not None and source.text else ""
    line_rate = float(root.get("line-rate", 0)) * 100
    branch_rate = float(root.get("branch-rate", 0)) * 100
    covered = int(root.get("lines-covered", 0))
    valid = int(root.get("lines-valid", 0))
    out.append(
        f"**{line_rate:.1f}%** of lines covered ({covered}/{valid}) · "
        f"**{branch_rate:.1f}%** of branches\n"
    )

    rows = []
    for cls in root.iter("class"):
        lines = list(cls.iter("line"))
        if not lines:
            continue
        stmts = len(lines)
        missed = sum(1 for ln in lines if int(ln.get("hits", 0)) == 0)
        name = cls.get("filename", "?")
        if not name.startswith(prefix):
            name = prefix + name
        rows.append((name, stmts, missed, (stmts - missed) / stmts * 100))

    if rows:
        out.append("| File | Stmts | Miss | Cover |")
        out.append("|------|------:|-----:|------:|")
        # Worst-covered first, so gaps are the first thing on the page.
        for name, stmts, missed, pct in sorted(rows, key=lambda r: (r[3], r[0])):
            mark = "" if missed == 0 else " ⚠️"
            out.append(f"| `{name}` | {stmts} | {missed} | {pct:.1f}%{mark} |")
        out.append("")


def main() -> int:
    out: list[str] = []
    test_section(out)
    coverage_section(out)
    body = "\n".join(out)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(body + "\n")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
