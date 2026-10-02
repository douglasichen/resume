#!/usr/bin/env python3
"""Compile an arbitrary résumé Markdown file to a PDF at a chosen path.

The canonical pipeline (watch.sh / LaTeX Workshop) always builds
resumes/resume.md -> build/resume.pdf. This CLI is for one-off variants: a
per-job tailored copy that must land somewhere else under its own name, without
touching resumes/resume.md, build/, or ready/.

Usage:
    python3 scripts/build_resume.py <input.md> <output.pdf> [options]
    python3 scripts/build_resume.py tailored/melissa.md tailored/melissa.pdf

Options:
    --max-pages N   fail if the PDF exceeds N pages (default 1, 0 = no limit)
    --json          emit one JSON object instead of a human line
    --keep-tex      copy the generated .tex next to the output PDF

Exit code is 0 on success, 1 on any failure; on success the PDF exists at the
requested path. Everything is compiled in a temp directory, so a failed build
never leaves a half-written PDF at the destination.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MD2TEX = REPO / "scripts" / "md2tex.py"
TEXBIN = "/Library/TeX/texbin"
PAGES_RE = re.compile(r"Output written on .*?\((\d+) pages?", re.S)

sys.path.insert(0, str(REPO / "scripts"))
try:
    from pdf_valid import pdf_issues
except Exception:  # pragma: no cover - validator is optional
    pdf_issues = None


class BuildError(Exception):
    def __init__(self, message: str, *, pages: int = 0):
        super().__init__(message)
        self.pages = pages


def _env() -> dict:
    env = os.environ.copy()
    if Path(TEXBIN).is_dir():
        env["PATH"] = TEXBIN + os.pathsep + env.get("PATH", "")
    return env


def _run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), env=_env(), capture_output=True, text=True, timeout=timeout
    )


def build(md: Path, out: Path, *, max_pages: int = 1, keep_tex: bool = False) -> dict:
    """Compile `md` to `out`. Returns {pdf, pages, bytes}; raises BuildError."""
    md = md.expanduser().resolve()
    if not md.is_file():
        raise BuildError(f"input markdown not found: {md}")
    if not MD2TEX.is_file():
        raise BuildError(f"md2tex.py not found: {MD2TEX}")

    out = out.expanduser()
    if out.is_dir() or str(out).endswith(os.sep):
        out = out / (md.stem + ".pdf")
    if out.suffix.lower() != ".pdf":
        out = out.with_suffix(".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="resume-build-") as tmp:
        tmpd = Path(tmp)
        tex = tmpd / (md.stem + ".tex")

        conv = _run([sys.executable, str(MD2TEX), str(md), str(tex)], REPO, 60)
        if conv.returncode != 0 or not tex.is_file():
            raise BuildError(f"md2tex failed: {(conv.stderr or conv.stdout).strip()[:900]}")

        # -outdir keeps aux files (and pdf_valid's ready/ copy) out of build/
        comp = _run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", f"-outdir={tmpd}", str(tex)],
            tmpd,
            180,
        )
        pdf = tmpd / (md.stem + ".pdf")
        if not pdf.is_file():
            log = tmpd / (md.stem + ".log")
            detail = ""
            if log.is_file():
                errs = [l for l in log.read_text(errors="replace").splitlines() if l.startswith("!")]
                detail = " | ".join(errs[:3])
            raise BuildError(
                f"latexmk produced no PDF: {detail or (comp.stderr or comp.stdout).strip()[:900]}"
            )

        data = pdf.read_bytes()
        pages = 0
        log = tmpd / (md.stem + ".log")
        if log.is_file():
            m = PAGES_RE.search(log.read_text(errors="replace"))
            if m:
                pages = int(m.group(1))
        if max_pages and pages > max_pages:
            raise BuildError(
                f"{pages} pages (limit {max_pages}) — trim bullets or restore the "
                f"`: \\vspace{{...}}` directives",
                pages=pages,
            )
        if pdf_issues is not None:
            issues = pdf_issues(data)
            if issues:
                raise BuildError("PDF failed structural validation: " + "; ".join(issues))

        # Only touch the destination once everything passed.
        shutil.copy2(pdf, out)
        if keep_tex:
            shutil.copy2(tex, out.with_suffix(".tex"))

    return {"pdf": str(out), "pages": pages, "bytes": len(data)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="build_resume.py", description="Compile a résumé .md to a PDF at a given path."
    )
    ap.add_argument("md", help="input Markdown résumé")
    ap.add_argument("out", help="output PDF path (a directory is allowed)")
    ap.add_argument("--max-pages", type=int, default=1, help="page limit; 0 disables (default 1)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--keep-tex", action="store_true", help="also write the .tex beside the PDF")
    a = ap.parse_args(argv)

    try:
        res = build(
            Path(a.md), Path(a.out), max_pages=a.max_pages, keep_tex=a.keep_tex
        )
    except BuildError as e:
        msg = str(e)
        extra = {"pages": e.pages} if e.pages else {}
    except subprocess.TimeoutExpired as e:
        msg = f"timed out after {e.timeout}s"
        extra = {}
    except Exception as e:  # unexpected; still a clean FAIL for the caller
        msg = f"{type(e).__name__}: {e}"
        extra = {}
    else:
        if a.json:
            print(json.dumps({"ok": True, **res}))
        else:
            pages = res["pages"] or "?"
            print(f"OK: {res['pdf']} ({pages} page{'' if pages == 1 else 's'}, {res['bytes']} bytes)")
        return 0

    if a.json:
        print(json.dumps({"ok": False, "error": msg, **extra}))
    else:
        print(f"FAIL: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
