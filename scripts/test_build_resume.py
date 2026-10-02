#!/usr/bin/env python3
"""Tests for scripts/build_resume.py (stdlib asserts, no framework).

Run: python3 scripts/test_build_resume.py
Compiles real PDFs via latexmk, so it needs MacTeX on PATH like the other tests.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_resume import BuildError, build  # noqa: E402

SOURCE = REPO / "resumes" / "resume.md"


def test_builds_to_exact_path(tmp: Path) -> None:
    out = tmp / "acme__swe-intern.pdf"
    res = build(SOURCE, out)
    assert out.is_file(), "PDF not written to the requested path"
    assert res["pages"] == 1, res
    assert out.read_bytes().startswith(b"%PDF-"), "not a PDF"
    print("  ok: builds to the exact path,", res["pages"], "page")


def test_directory_out_derives_name(tmp: Path) -> None:
    d = tmp / "into-a-dir"
    d.mkdir()
    res = build(SOURCE, d)
    assert Path(res["pdf"]) == d / "resume.pdf", res
    print("  ok: directory out ->", Path(res["pdf"]).name)


def test_page_limit_fails_and_writes_nothing(tmp: Path) -> None:
    """The Acima failure mode: \\vspace stripped + bullets padded -> >1 page."""
    src = SOURCE.read_text(encoding="utf-8")
    src = re.sub(r"^: \\vspace.*$\n?", "", src, flags=re.M)
    bullets = [l for l in src.splitlines() if l.startswith("- ") and "**" in l]
    fat = tmp / "fat.md"
    fat.write_text(src + "\n".join(bullets * 3) + "\n", encoding="utf-8")

    out = tmp / "must-not-exist.pdf"
    try:
        build(fat, out)
    except BuildError as e:
        assert "limit 1" in str(e), e
        assert not out.exists(), "a failed build left a PDF at the destination"
        print("  ok: page limit rejects and leaves no file —", str(e)[:48])
    else:
        raise AssertionError("expected BuildError for a multi-page resume")


def test_max_pages_zero_allows_overflow(tmp: Path) -> None:
    src = SOURCE.read_text(encoding="utf-8")
    bullets = [l for l in src.splitlines() if l.startswith("- ") and "**" in l]
    fat = tmp / "fat2.md"
    fat.write_text(src + "\n".join(bullets * 3) + "\n", encoding="utf-8")
    res = build(fat, tmp / "ok-long.pdf", max_pages=0)
    assert res["pages"] > 1, res
    print("  ok: --max-pages 0 allows", res["pages"], "pages")


def test_missing_input(tmp: Path) -> None:
    try:
        build(tmp / "nope.md", tmp / "x.pdf")
    except BuildError as e:
        assert "not found" in str(e), e
        print("  ok: missing input rejected")
    else:
        raise AssertionError("expected BuildError for a missing input")


def test_does_not_touch_repo_outputs(tmp: Path) -> None:
    """Per-job builds must not overwrite build/resume.pdf or push to ready/."""
    build_pdf = REPO / "build" / "resume.pdf"
    ready = REPO / "ready"
    before_build = build_pdf.stat().st_mtime if build_pdf.exists() else None
    before_ready = sorted(p.name for p in ready.glob("*.pdf")) if ready.is_dir() else []

    build(SOURCE, tmp / "isolated.pdf")

    after_build = build_pdf.stat().st_mtime if build_pdf.exists() else None
    after_ready = sorted(p.name for p in ready.glob("*.pdf")) if ready.is_dir() else []
    assert before_build == after_build, "build/resume.pdf was modified"
    assert before_ready == after_ready, "ready/ was modified"
    print("  ok: build/ and ready/ untouched")


def main() -> int:
    if not SOURCE.is_file():
        print("SKIP: resumes/resume.md missing")
        return 0
    print("build_resume:")
    with tempfile.TemporaryDirectory(prefix="test-build-resume-") as t:
        tmp = Path(t)
        for fn in (
            test_builds_to_exact_path,
            test_directory_out_derives_name,
            test_page_limit_fails_and_writes_nothing,
            test_max_pages_zero_allows_overflow,
            test_missing_input,
            test_does_not_touch_repo_outputs,
        ):
            fn(tmp)
    print("BUILD_RESUME OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
