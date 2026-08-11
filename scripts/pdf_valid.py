#!/usr/bin/env python3
"""Validate that a PDF is structurally well-formed enough for strict parsers.

Resume checkers (and tools like pdfinfo) reject files that Preview still opens.
The failure mode we hit: a valid PDF followed by junk + a second broken
startxref/%%EOF, so the final trailer points into a stream.

Wired into every latexmk success via .latexmkrc (async — does not slow rebuilds).

On success for build/<name>.pdf, also copies to ready/<name>-<timestamp>.pdf
(only when valid — an invalid build never touches ready/).

Usage:
    python3 pdf_valid.py path/to/file.pdf          # exit 0 ok, 1 bad
    python3 pdf_valid.py --async path/to/file.pdf  # spawn check in background, exit 0
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime


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


def ready_dir_for(pdf_path: str) -> str | None:
    """Return <repo>/ready if pdf_path is under <repo>/build/, else None.

    ready/ is only updated for real build outputs — unit-test temp PDFs are ignored.
    """
    abs_p = os.path.abspath(pdf_path)
    parent = os.path.dirname(abs_p)
    if os.path.basename(parent) != "build":
        return None
    return os.path.join(os.path.dirname(parent), "ready")


# ready/ is a FIFO queue of sendable PDFs: push on valid build, pop oldest
# when over capacity so we never pile up dozens of copies.
READY_MAX_COPIES = 10


def ready_pdf_path(pdf_path: str, when: datetime | None = None) -> str | None:
    """Path for ready/<stem>-YYYYMMDD-HHMMSS.pdf, or None if not a build/ PDF."""
    rdir = ready_dir_for(pdf_path)
    if rdir is None:
        return None
    when = when or datetime.now()
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    ts = when.strftime("%Y%m%d-%H%M%S")
    return os.path.join(rdir, f"{stem}-{ts}.pdf")


def prune_ready(ready_dir: str, stem: str, keep: int = READY_MAX_COPIES) -> list[str]:
    """FIFO: if more than `keep` ready/<stem>-*.pdf, delete oldest first.

    Timestamped names (YYYYMMDD-HHMMSS) sort oldest→newest as text. Returns
    paths that were removed (front of the queue).
    """
    if keep < 0 or not os.path.isdir(ready_dir):
        return []
    prefix = stem + "-"
    files = []
    for name in os.listdir(ready_dir):
        if not (name.startswith(prefix) and name.endswith(".pdf")):
            continue
        if name.endswith(".tmp"):
            continue
        files.append(os.path.join(ready_dir, name))
    # Oldest first = queue order; pop from the front until len <= keep.
    files.sort(key=os.path.basename)
    overflow = len(files) - keep
    removed: list[str] = []
    for old in files[: max(overflow, 0)]:
        try:
            os.remove(old)
            removed.append(old)
        except OSError:
            pass
    return removed


def publish_ready(pdf_path: str, data: bytes, when: datetime | None = None) -> str | None:
    """Push a valid PDF onto the ready/ FIFO queue. Returns dest path, or None.

    Never called on invalid PDFs — callers must only invoke after validation passes.
    Atomic write (tmp + replace) so a partial copy cannot look "ready".
    After push, pops oldest copies until at most READY_MAX_COPIES remain.
    """
    dest = ready_pdf_path(pdf_path, when=when)
    if dest is None:
        return None
    ready_dir = os.path.dirname(dest)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    os.makedirs(ready_dir, exist_ok=True)
    tmp = dest + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dest)  # push newest
    removed = prune_ready(ready_dir, stem, keep=READY_MAX_COPIES)  # pop oldest
    if removed:
        sys.stdout.write(
            f"[pdf-valid] ready/ queue: dropped {len(removed)} oldest "
            f"(cap {READY_MAX_COPIES})\n"
        )
    return dest


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
        # Do NOT touch ready/ — last good ready/<name>-<timestamp>.pdf stays.
        sys.stderr.write(
            f"\n[pdf-valid] *** INVALID PDF — do not send this file out ***\n"
            f"[pdf-valid] {path}\n"
            f"[pdf-valid] ready/ not updated (still has last valid copy, if any)\n"
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

    # Clean success: drop any prior failure marker, then promote to ready/.
    try:
        if os.path.exists(mark):
            os.remove(mark)
    except OSError:
        pass
    sys.stdout.write(f"[pdf-valid] {path}: ok ({len(data)} bytes)\n")
    try:
        dest = publish_ready(path, data)
        if dest is not None:
            sys.stdout.write(f"[pdf-valid] ready copy: {dest}\n")
    except OSError as e:
        sys.stderr.write(f"[pdf-valid] failed to write ready/ copy: {e}\n")
        # Validation itself passed; ready/ failure is non-fatal for exit code.
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
