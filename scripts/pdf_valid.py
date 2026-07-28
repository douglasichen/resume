#!/usr/bin/env python3
"""Validate that a PDF is structurally well-formed enough for strict parsers.

Resume checkers (and tools like pdfinfo) reject files that Preview still opens.
The failure mode we hit: a valid PDF followed by junk + a second broken
startxref/%%EOF, so the final trailer points into a stream.

Wired into every latexmk success via .latexmkrc (async — does not slow rebuilds).

Usage:
    python3 pdf_valid.py path/to/file.pdf          # exit 0 ok, 1 bad
    python3 pdf_valid.py --async path/to/file.pdf  # spawn check in background, exit 0
"""
from __future__ import annotations

import os
import re
import subprocess
import sys


def pdf_issues(data: bytes) -> list[str]:
    """Return human-readable structural problems, or [] if the PDF looks fine.

    Checks (stdlib only — no poppler/qpdf required):
      - %PDF- header
      - exactly one %%EOF, with only trailing whitespace after it
      - exactly one startxref
      - startxref offset points at a classic xref table or an /XRef stream obj
    """
    issues: list[str] = []
    if not data.startswith(b"%PDF-"):
        issues.append("missing %PDF- header")
        return issues

    eof_count = data.count(b"%%EOF")
    if eof_count == 0:
        issues.append("missing %%EOF")
        return issues
    if eof_count != 1:
        issues.append(f"expected 1 %%EOF, found {eof_count}")

    first_eof = data.find(b"%%EOF")
    after = data[first_eof + 5 :]
    if after.strip():
        issues.append(
            f"junk after first %%EOF ({len(after.strip())} non-whitespace bytes)"
        )

    sx_count = data.count(b"startxref")
    if sx_count == 0:
        issues.append("missing startxref")
        return issues
    if sx_count != 1:
        issues.append(f"expected 1 startxref, found {sx_count}")

    m = re.search(rb"startxref\s+(\d+)\s*%%EOF", data)
    if not m:
        issues.append("could not parse startxref/%%EOF pair")
        return issues

    off = int(m.group(1))
    if off < 0 or off >= len(data):
        issues.append(f"startxref offset {off} out of range (file size {len(data)})")
        return issues

    chunk = data[off : off + 400]
    if chunk.startswith(b"xref"):
        return issues  # classic cross-reference table

    if re.match(rb"\d+\s+0\s+obj", chunk):
        # pdfTeX emits a compressed xref stream: N 0 obj << /Type /XRef ...
        # Allow optional whitespace between /Type and /XRef.
        if not re.search(rb"/Type\s*/XRef", chunk):
            issues.append(
                "startxref points at an object without /Type /XRef "
                f"(got {chunk[:48]!r})"
            )
        return issues

    issues.append(
        "startxref does not point at an xref table or /XRef stream "
        f"(got {chunk[:48]!r})"
    )
    return issues


def is_valid_pdf(data: bytes) -> bool:
    return not pdf_issues(data)


def marker_path(pdf_path: str) -> str:
    """Sidecar file written on failure so a bad PDF is hard to miss."""
    return pdf_path + ".INVALID"


def _notify_macos(title: str, body: str) -> None:
    """Best-effort desktop notification (macOS). Silent no-op elsewhere."""
    if sys.platform != "darwin":
        return
    # Escape for AppleScript string literals.
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    script = f'display notification "{esc(body)}" with title "{esc(title)}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def check_file(path: str) -> int:
    """Validate path; manage .INVALID marker; return process exit code."""
    try:
        data = open(path, "rb").read()
    except OSError as e:
        sys.stderr.write(f"[pdf-valid] {path}: {e}\n")
        return 2

    issues = pdf_issues(data)
    mark = marker_path(path)
    if issues:
        try:
            with open(mark, "w") as f:
                f.write(f"{path}: INVALID\n")
                for issue in issues:
                    f.write(f"  - {issue}\n")
        except OSError:
            pass
        sys.stderr.write(
            f"\n[pdf-valid] *** INVALID PDF — do not send this file out ***\n"
            f"[pdf-valid] {path}\n"
        )
        for issue in issues:
            sys.stderr.write(f"[pdf-valid]   - {issue}\n")
        sys.stderr.write(
            f"[pdf-valid] marker: {mark}\n"
            f"[pdf-valid] rebuild cleanly: rm -f build/* && "
            f"python3 scripts/md2tex.py resumes/resume.md resumes/resume.tex "
            f"&& latexmk -g resumes/resume.tex\n\n"
        )
        _notify_macos(
            "Resume PDF INVALID",
            f"{os.path.basename(path)} failed structural checks — do not upload",
        )
        return 1

    # Clean success: drop any prior failure marker.
    try:
        if os.path.exists(mark):
            os.remove(mark)
    except OSError:
        pass
    sys.stdout.write(f"[pdf-valid] {path}: ok ({len(data)} bytes)\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    async_mode = False
    if argv and argv[0] == "--async":
        async_mode = True
        argv = argv[1:]
    if len(argv) != 1:
        sys.stderr.write(
            "usage: pdf_valid.py [--async] path/to/file.pdf\n"
        )
        return 2
    path = argv[0]

    if async_mode:
        # Detach so latexmk $success_cmd returns immediately and never fails
        # the build because of our check. Child inherits stdio so VSCode /
        # watch.sh terminal panels still show pass/fail lines.
        try:
            subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), path],
                start_new_session=True,
            )
        except OSError as e:
            sys.stderr.write(f"[pdf-valid] failed to spawn async check: {e}\n")
            return 2
        return 0

    return check_file(path)


if __name__ == "__main__":
    sys.exit(main())
