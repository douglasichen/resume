#!/usr/bin/env python3
"""Test suite for md2tex.py (and PDF structural validity).

Covers unit behaviour (escaping, bold, links, field splitting, section dispatch,
directives), end-to-end LaTeX compilation of adversarial inputs, and PDF
structure checks so resume checkers don't reject a corrupt file that Preview
still opens.

Run:  python3 test_md2tex.py
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("md2tex", os.path.join(HERE, "md2tex.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
spec_pdf = importlib.util.spec_from_file_location(
    "pdf_valid", os.path.join(HERE, "pdf_valid.py"))
PV = importlib.util.module_from_spec(spec_pdf)
spec_pdf.loader.exec_module(PV)

# ---------------------------------------------------------------- test harness
_passed = []
_failed = []


def check(name, cond, detail=""):
    (_passed if cond else _failed).append(name)
    mark = "ok  " if cond else "FAIL"
    line = f"[{mark}] {name}"
    if not cond and detail:
        line += f"\n        {detail}"
    print(line)


def eq(name, got, want):
    check(name, got == want, f"got:  {got!r}\n        want: {want!r}")


# ---------------------------------------------------------------- esc()
eq("esc: ampersand", M.esc("A & B"), r"A \& B")
eq("esc: percent", M.esc("70%"), r"70\%")
eq("esc: dollar", M.esc("$5K"), r"\$5K")
eq("esc: hash", M.esc("C#"), r"C\#")
eq("esc: underscore", M.esc("a_b"), r"a\_b")
eq("esc: all-at-once", M.esc("a&b%c$d#e_f"), r"a\&b\%c\$d\#e\_f")
eq("esc: nothing-to-do", M.esc("plain text 1.0 C++"), "plain text 1.0 C++")
eq("esc: empty", M.esc(""), "")

# ---------------------------------------------------------------- conv() (esc + bold)
eq("conv: single bold", M.conv("**hi**"), r"\textbf{hi}")
eq("conv: bold in sentence", M.conv("a **b** c"), r"a \textbf{b} c")
eq("conv: two bolds", M.conv("**a** and **b**"), r"\textbf{a} and \textbf{b}")
eq("conv: bold wraps special", M.conv("**$5K**"), r"\textbf{\$5K}")
eq("conv: special outside bold", M.conv("save **70%** now & later"),
   r"save \textbf{70\%} now \& later")
eq("conv: no bold", M.conv("just text"), "just text")

# ---------------------------------------------------------------- split_link()
eq("link: none", M.split_link("Plain Org"), ("Plain Org", None, None))
eq("link: only link", M.split_link("[Demo](http://x.com)"),
   ("", "Demo", "http://x.com"))
eq("link: text + link", M.split_link("Exchange Solutions [Demo](http://x.com)"),
   ("Exchange Solutions", "Demo", "http://x.com"))
eq("link: url with query/specials kept raw",
   M.split_link("[L](https://y.com/watch?v=a_b&t=1)"),
   ("", "L", "https://y.com/watch?v=a_b&t=1"))

# ---------------------------------------------------------------- fields()
eq("fields: basic", M.fields("a | b | c"), ["a", "b", "c"])
eq("fields: strip", M.fields("  a  |b|  c  "), ["a", "b", "c"])
eq("fields: trailing pipe -> empty", M.fields("a | b |"), ["a", "b", ""])
eq("fields: single", M.fields("solo"), ["solo"])

# ---------------------------------------------------------------- sectype_for()
eq("sectype: education", M.sectype_for("Education"), "subheading")
eq("sectype: projects", M.sectype_for("Projects"), "project")
eq("sectype: personal projects", M.sectype_for("Personal Projects"), "project")
eq("sectype: skills", M.sectype_for("Skills"), "skills")
eq("sectype: case-insensitive", M.sectype_for("  EDUCATION "), "subheading")
eq("sectype: unknown -> subheadingB", M.sectype_for("Volunteering"), "subheadingB")

# ---------------------------------------------------------------- emit_skills()
sk1 = M.emit_skills(["Languages: Python, C++"])
check("skills: single line has no trailing backslash",
      not any(r.rstrip().endswith(r"\\") for r in sk1),
      "\n".join(sk1))
sk2 = M.emit_skills(["Languages: Python", "Tools: AWS & Docker"])
joined2 = "\n".join(sk2)
check("skills: two lines joined with \\\\", r"\textbf{Languages:}{ Python} \\" in joined2, joined2)
check("skills: specials escaped in values", r"AWS \& Docker" in joined2, joined2)

# ---------------------------------------------------------------- emit_entry()
edu = M.emit_entry("subheading",
                   {"header": "UBC | Vancouver | BSc CS | 2023 -- 2028", "items": []})
check("entry/edu: resumeSubheading shape",
      edu[0].strip() == r"\resumeSubheading"
      and "{UBC}{Vancouver}" in edu[1]
      and "{BSc CS}{2023 -- 2028}" in edu[2],
      "\n".join(edu))

projL = M.emit_entry("project",
                     {"header": "MyApp | TS, React | [Repo](http://g.com/x)", "items": []})
pj = "\n".join(projL)
check("entry/proj: textbf name + emph stack", r"\textbf{MyApp} $|$ \emph{TS, React" in pj, pj)
check("entry/proj: href with underline label",
      r"\href{http://g.com/x}{{\underline{Repo}}}" in pj, pj)

projN = M.emit_entry("project", {"header": "MyApp | TS, React", "items": []})
check("entry/proj: no link -> no href",
      "href" not in "\n".join(projN), "\n".join(projN))

projM = M.emit_entry("project",
                     {"header": "MyApp | TS, React | [Code](http://g.com/x) [Launch Post](http://l.com/y)",
                      "items": []})
pjm = "\n".join(projM)
check("entry/proj: two links both rendered",
      r"\href{http://g.com/x}{{\underline{Code}}}" in pjm
      and r"\href{http://l.com/y}{{\underline{Launch Post}}}" in pjm, pjm)
check("entry/proj: two links joined with $|$",
      r"{{\underline{Code}}} $|$ \href{http://l.com/y}" in pjm, pjm)

projPipe = M.emit_entry("project",
                        {"header": "Dance CV | AI coach | [Devpost](http://d.com/x) | [Code](http://g.com/y)",
                         "items": []})
pjp = "\n".join(projPipe)
check("entry/proj: pipe-separated links both rendered",
      r"\href{http://d.com/x}{{\underline{Devpost}}}" in pjp
      and r"\href{http://g.com/y}{{\underline{Code}}}" in pjp, pjp)
check("entry/proj: pipe-separated links joined with $|$",
      r"{{\underline{Devpost}}} $|$ \href{http://g.com/y}" in pjp, pjp)

expO = M.emit_entry("subheadingB",
                    {"header": "Engineer | Acme [Demo](http://d.com) | 2024", "items": []})
ex = "\n".join(expO)
check("entry/expB: org link rendered",
      r"Acme $|$ \underline{\href{http://d.com}{Demo}}" in ex, ex)
check("entry/expB: arg order title/date/org",
      r"\resumeSubheadingB{Engineer}{2024}{Acme" in ex, ex)

# ---------------------------------------------------------------- emit_bullets() / directives
b_inline = M.emit_bullets([("bullet", "one"), ("raw", r"\vspace{-12pt}"), ("bullet", "two")])
txt = "\n".join(b_inline)
check("bullets: inline directive between bullets",
      r"\vspace{-12pt}" in txt
      and txt.index("one") < txt.index("-12pt") < txt.index("two"), txt)
b_trail = M.emit_bullets([("bullet", "only"), ("raw", r"\vspace{-10pt}")])
end_line = [l for l in b_trail if "resumeItemListEnd" in l][0]
check("bullets: trailing directive attaches to ListEnd",
      end_line.strip() == r"\resumeItemListEnd\vspace{-10pt}", end_line)

# ---------------------------------------------------------------- parse()
MD = """# Jane Doe
- jane@x.com | mailto:jane@x.com
- site.com | https://site.com

## Education
### UBC | Vancouver | BSc | 2023 -- 2028
- Courses: A, B

## Skills
- Languages: Python

## Work Experience
### Eng | Acme | 2024
- Did **things** & stuff
: \\vspace{-5pt}
"""
doc = M.parse(MD)
eq("parse: name", doc["name"], "Jane Doe")
eq("parse: contacts count", len(doc["contacts"]), 2)
eq("parse: sections count", len(doc["sections"]), 3)
eq("parse: edu entries", len(doc["sections"][0]["entries"]), 1)
eq("parse: skills bullets", doc["sections"][1]["bullets"], ["Languages: Python"])
work = doc["sections"][2]["entries"][0]
eq("parse: work bullet+directive items",
   [k for k, _ in work["items"]], ["bullet", "raw"])

# ---------------------------------------------------------------- full emit wrapping
full = M.PREAMBLE + M.emit(doc) + M.FOOTER
check("full: starts with documentclass-bearing preamble",
      full.startswith(M.PREAMBLE) and r"\begin{document}" in full, "")
check("full: ends with end{document}", full.rstrip().endswith(r"\end{document}"), "")
check("full: has all sections",
      all(s in full for s in [r"\section{Education}", r"\section{Skills}",
                              r"\section{Work Experience}"]), "")
check("full: bold + escape applied in body",
      r"\textbf{things} \& stuff" in full, "")

# ---------------------------------------------------------------- ROBUSTNESS / edge cases
# Contact line lacking a pipe should not crash.
try:
    M.parse("# X\n- noseparator\n")
    d = M.parse("# X\n- noseparator\n")
    M.emit(d)
    check("edge: contact without '|' does not crash", True)
except Exception as e:
    check("edge: contact without '|' does not crash", False, f"raised {type(e).__name__}: {e}")

# Empty document (name only).
try:
    M.emit(M.parse("# Solo\n"))
    check("edge: name-only doc does not crash", True)
except Exception as e:
    check("edge: name-only doc does not crash", False, f"raised {type(e).__name__}: {e}")

# Entry with zero bullets should not emit an item list.
no_b = M.emit_entry("subheadingB", {"header": "T | O | D", "items": []})
check("edge: entry with no bullets omits ItemListStart",
      not any("resumeItemListStart" in l for l in no_b), "\n".join(no_b))

# Section with bullets but no ### under a non-skills section: bullets shouldn't crash.
try:
    M.emit(M.parse("# X\n## Work Experience\n- orphan bullet\n"))
    check("edge: orphan bullet in non-skills section does not crash", True)
except Exception as e:
    check("edge: orphan bullet does not crash", False, f"{type(e).__name__}: {e}")

# Curly braces in user text (LaTeX-significant) -- documents whether they're handled.
braces = M.conv("uses {curly} braces")
check("edge: curly braces escaped (avoid LaTeX breakage)",
      r"\{" in braces and r"\}" in braces,
      f"NOT escaped -> {braces!r} (would break LaTeX)")

# Backslash in user text.
bs = M.conv(r"path\to\file")
check("edge: backslash escaped",
      r"\textbackslash" in bs,
      f"NOT escaped -> {bs!r} (would break LaTeX)")

# ---------------------------------------------------------------- clean_md()
eq("clean: drops full-line HTML comments",
   M.clean_md("# N\n<!-- - old bullet -->\n- keep\n"),
   "# N\n- keep\n")
eq("clean: drops : \\vspace lines",
   M.clean_md("# N\n- b\n: \\vspace{-8pt}\n\n## S\n"),
   "# N\n- b\n\n## S\n")
eq("clean: drops commented vspace",
   M.clean_md("# N\n<!-- : \\vspace{-10pt} -->\n## S\n"),
   "# N\n## S\n")
eq("clean: collapses blank runs left by removed comments",
   M.clean_md("# N\n\n<!-- x -->\n\n- b\n"),
   "# N\n\n- b\n")
eq("clean: keeps real bullets and links",
   M.clean_md("### Job | Org [Demo](http://x.com) | 2024\n- did **thing**\n"),
   "### Job | Org [Demo](http://x.com) | 2024\n- did **thing**\n")
# Path layout: .../resumes/resume.md -> .../build/clean-resume.md
with tempfile.TemporaryDirectory() as d:
    resumes_dir = os.path.join(d, "resumes")
    os.makedirs(resumes_dir)
    src = os.path.join(resumes_dir, "resume.md")
    open(src, "w").write("# A\n")
    cp = M.clean_md_path(src)
    eq("clean_md_path: basename is clean-resume.md",
       os.path.basename(cp), "clean-resume.md")
    eq("clean_md_path: lives under build/",
       os.path.basename(os.path.dirname(cp)), "build")
    eq("clean_md_path: build is sibling of resumes/",
       os.path.dirname(os.path.dirname(cp)), d)

eq("clean_md_path: clean-* is not re-cleaned",
   M.clean_md_path("build/clean-resume.md"),
   None)

# Round-trip: writing clean file under build/ next to a resumes/ source.
with tempfile.TemporaryDirectory() as d:
    resumes_dir = os.path.join(d, "resumes")
    os.makedirs(resumes_dir)
    src = os.path.join(resumes_dir, "resume.md")
    open(src, "w").write("# A\n<!-- hide -->\n- show\n: \\vspace{-1pt}\n")
    cp = M.clean_md_path(src)
    os.makedirs(os.path.dirname(cp), exist_ok=True)
    open(cp, "w").write(M.clean_md(open(src).read()))
    check("clean: writes build/clean-resume.md",
          os.path.isfile(cp)
          and os.path.basename(cp) == "clean-resume.md"
          and os.path.basename(os.path.dirname(cp)) == "build")
    eq("clean: build copy content stripped",
       open(cp).read(),
       "# A\n- show\n")

# ---------------------------------------------------------------- PDF validity
# Minimal classic-xref PDF (offsets must match body layout).
_MIN_PDF_BODY = b"""\
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
"""


def _classic_pdf() -> bytes:
    """Build a tiny well-formed PDF with a classic xref table."""
    body = _MIN_PDF_BODY
    # Object starts for xref (byte offsets of "N 0 obj" lines).
    offs = [body.find(b"%d 0 obj" % n) for n in (1, 2, 3)]
    xref_off = len(body)
    xref = [b"xref\n0 4\n", b"0000000000 65535 f \n"]
    for o in offs:
        xref.append(f"{o:010d} 00000 n \n".encode())
    xref_block = b"".join(xref)
    trailer = (
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_off).encode() + b"\n%%EOF\n"
    )
    return body + xref_block + trailer


def _xref_stream_pdf() -> bytes:
    """Build a tiny PDF whose startxref points at a /Type /XRef stream obj.

    Layout mirrors pdfTeX output (compressed xref stream at end).
    """
    # Body objects first; then a stub xref stream object; startxref -> that obj.
    body = (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    )
    xref_obj_off = len(body)
    # Empty stream is fine for structure checks; we only require /Type /XRef.
    xref_obj = (
        b"3 0 obj\n"
        b"<< /Type /XRef /Size 4 /W [1 1 1] /Root 1 0 R /Length 0 >>\n"
        b"stream\n"
        b"endstream\n"
        b"endobj\n"
    )
    tail = b"startxref\n" + str(xref_obj_off).encode() + b"\n%%EOF\n"
    return body + xref_obj + tail


good = _classic_pdf()
eq("pdf: classic well-formed has no issues", PV.pdf_issues(good), [])
check("pdf: classic is_valid_pdf", PV.is_valid_pdf(good))

good_stream = _xref_stream_pdf()
eq("pdf: xref-stream well-formed has no issues", PV.pdf_issues(good_stream), [])

# Regression: the failure mode resume checkers hit — valid PDF + junk + broken
# second startxref/%%EOF so the final trailer points into a content stream.
corrupt = good + b"FB3EFDBEA\x00\x01GARBAGE\nstartxref\n12\n%%EOF\n"
issues = PV.pdf_issues(corrupt)
check("pdf: junk-after-EOF is invalid", not PV.is_valid_pdf(corrupt), issues)
check("pdf: junk-after-EOF reports junk",
      any("junk after first %%EOF" in i for i in issues), issues)
check("pdf: junk-after-EOF reports multiple %%EOF",
      any("expected 1 %%EOF" in i for i in issues), issues)
check("pdf: junk-after-EOF reports multiple startxref",
      any("expected 1 startxref" in i for i in issues), issues)

# startxref pointing into the middle of a stream/object (not an xref).
bad_ptr = (
    b"%PDF-1.7\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"stream\nNOT_AN_XREF_TABLE_HERE\nendstream\n"
    b"startxref\n" + str(len(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"))
    .encode() + b"\n%%EOF\n"
)
bad_ptr_issues = PV.pdf_issues(bad_ptr)
check("pdf: startxref into stream body is invalid",
      not PV.is_valid_pdf(bad_ptr), bad_ptr_issues)
check("pdf: bad startxref target is reported",
      any("does not point" in i or "without /Type /XRef" in i for i in bad_ptr_issues),
      bad_ptr_issues)

eq("pdf: missing header",
   PV.pdf_issues(b"not a pdf%%EOF\n")[0].startswith("missing %PDF-"), True)
check("pdf: empty is invalid", not PV.is_valid_pdf(b""))

# Truncating at the first %%EOF of a corrupt file must restore validity
# (the recovery path we used when diagnosing the checker rejection).
first_eof = corrupt.find(b"%%EOF")
recovered = corrupt[: first_eof + 5] + b"\n"
check("pdf: truncate-at-first-EOF recovers classic PDF",
      PV.is_valid_pdf(recovered), PV.pdf_issues(recovered))

# check_file + .INVALID marker lifecycle (what runs after every latexmk success).
with tempfile.TemporaryDirectory() as d:
    good_path = os.path.join(d, "good.pdf")
    bad_path = os.path.join(d, "bad.pdf")
    open(good_path, "wb").write(good)
    open(bad_path, "wb").write(corrupt)
    # Silence notifications / stdout noise for the unit checks.
    rc_ok = PV.check_file(good_path)
    rc_bad = PV.check_file(bad_path)
    check("pdf: check_file ok exits 0", rc_ok == 0, f"rc={rc_ok}")
    check("pdf: check_file bad exits 1", rc_bad == 1, f"rc={rc_bad}")
    check("pdf: no .INVALID marker on success",
          not os.path.exists(PV.marker_path(good_path)))
    check("pdf: writes .INVALID marker on failure",
          os.path.exists(PV.marker_path(bad_path)))
    # A later successful check must clear a prior marker.
    open(bad_path, "wb").write(good)
    PV.check_file(bad_path)
    check("pdf: success clears prior .INVALID marker",
          not os.path.exists(PV.marker_path(bad_path)))

# --async must return immediately with 0 and still produce the check result.
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "async.pdf")
    open(p, "wb").write(corrupt)
    rc = subprocess.run(
        [sys.executable, os.path.join(HERE, "pdf_valid.py"), "--async", p],
        capture_output=True, text=True, timeout=5,
    )
    check("pdf: --async exits 0 immediately", rc.returncode == 0, rc.stderr)
    # Wait for the detached child to finish writing the marker.
    mark = PV.marker_path(p)
    for _ in range(50):
        if os.path.exists(mark):
            break
        import time
        time.sleep(0.05)
    check("pdf: --async child writes .INVALID for corrupt PDF",
          os.path.exists(mark), f"marker missing after wait; stderr={rc.stderr!r}")

# ---------------------------------------------------------------- COMPILE tests
def compile_ok(md_text, label):
    tex = M.PREAMBLE + M.emit(M.parse(md_text)) + M.FOOTER
    with tempfile.TemporaryDirectory() as d:
        tf = os.path.join(d, "t.tex")
        open(tf, "w").write(tex)
        env = dict(os.environ, PATH="/Library/TeX/texbin:" + os.environ.get("PATH", ""))
        r = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
             "-outdir=" + d, tf],
            cwd=d, env=env, capture_output=True, text=True)
        pdf_path = os.path.join(d, "t.pdf")
        ok = r.returncode == 0 and os.path.exists(pdf_path)
        detail = ""
        if not ok:
            errs = [l for l in (r.stdout + r.stderr).splitlines()
                    if l.startswith("!") or "Error" in l or ".tex:" in l]
            detail = "\n        ".join(errs[:6]) or "(no pdf produced)"
        check("compile: " + label, ok, detail)
        if ok:
            pdf_bytes = open(pdf_path, "rb").read()
            pi = PV.pdf_issues(pdf_bytes)
            check("compile/pdf-valid: " + label, not pi,
                  "\n        ".join(pi) if pi else "")


have_latexmk = subprocess.run(["bash", "-lc", "PATH=/Library/TeX/texbin:$PATH which latexmk"],
                              capture_output=True).returncode == 0
if not have_latexmk:
    print("[skip] latexmk not found -- skipping compilation tests")
else:
    # Regression: $success_cmd in .latexmkrc must fire pdf_valid after a real build.
    # Build a minimal doc from the repo root so .latexmkrc is picked up, then wait
    # for the async child to leave (or not leave) a .INVALID marker.
    def latexmk_success_cmd_runs_validator():
        import time
        with tempfile.TemporaryDirectory() as d:
            # Copy the real .latexmkrc behaviour: out_dir + success_cmd, but write
            # into this temp dir so we don't clobber build/.
            md = "# Async Check\n- a@b.com | mailto:a@b.com\n\n## Work Experience\n### R | O | 2024\n- bullet\n"
            tex = M.PREAMBLE + M.emit(M.parse(md)) + M.FOOTER
            tex_path = os.path.join(d, "t.tex")
            open(tex_path, "w").write(tex)
            rc_path = os.path.join(d, ".latexmkrc")
            # success_cmd path must resolve pdf_valid.py from the repo scripts/.
            valid_py = os.path.join(HERE, "pdf_valid.py")
            open(rc_path, "w").write(
                f"$out_dir = '.';\n"
                f"$pdf_mode = 1;\n"
                f"$success_cmd = 'python3 {valid_py} --async %D';\n"
            )
            env = dict(os.environ, PATH="/Library/TeX/texbin:" + os.environ.get("PATH", ""))
            r = subprocess.run(
                ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                 "-r", rc_path, tex_path],
                cwd=d, env=env, capture_output=True, text=True, timeout=120,
            )
            pdf_path = os.path.join(d, "t.pdf")
            if r.returncode != 0 or not os.path.exists(pdf_path):
                check("latexmk/success_cmd: build produced pdf", False,
                      (r.stdout + r.stderr)[-500:])
                return
            # Async child should clear/never write INVALID for a good PDF; give it a moment.
            mark = PV.marker_path(pdf_path)
            time.sleep(0.3)
            # Also require the PDF itself is structurally valid (sync check).
            pi = PV.pdf_issues(open(pdf_path, "rb").read())
            check("latexmk/success_cmd: produced PDF is well-formed", not pi,
                  "\n        ".join(pi) if pi else "")
            check("latexmk/success_cmd: no .INVALID marker after good build",
                  not os.path.exists(mark))

    latexmk_success_cmd_runs_validator()

    compile_ok("""# Test Person
- t@x.com | mailto:t@x.com

## Education
### School | City | Degree & Honors | 2020 -- 2024
- Took **hard** courses: 100% effort, $0 debt, A_grade, C# & C++

## Skills
- Languages: Python, C++, C#, F#
- Tools: AWS & GCP, 50% Docker

## Work Experience
### Engineer | Acme [Demo](https://y.com/watch?v=a_b&z=1) | 2024
- Saved **$5K** & boosted speed by **20x** (100% uptime)
: \\vspace{-6pt}

## Personal Projects
### App #1 | TS & React | [Repo](https://g.com/u/r_x?tab=1&q=2)
- Hit **1M+** users at 99.9% retention
""", "all specials, links, bold, directives")

    compile_ok("""# Minimal
- a@b.com | mailto:a@b.com

## Work Experience
### Role | Org | 2024
- One simple bullet
""", "minimal document")

    # Full real resume source — catches layout/content regressions that also
    # produce a checker-rejected PDF.
    real_md = os.path.join(REPO, "resumes", "resume.md")
    if os.path.isfile(real_md):
        compile_ok(open(real_md).read(), "real resumes/resume.md")

# If build/resume.pdf already exists (dev machine mid-edit), refuse a corrupt one.
built = os.path.join(REPO, "build", "resume.pdf")
if os.path.isfile(built):
    bi = PV.pdf_issues(open(built, "rb").read())
    check("pdf: existing build/resume.pdf is well-formed",
          not bi, "\n        ".join(bi) if bi else "")
else:
    print("[skip] build/resume.pdf not present -- skipping on-disk PDF check")

# ---------------------------------------------------------------- summary
print("\n" + "=" * 50)
print(f"PASSED {len(_passed)}   FAILED {len(_failed)}")
if _failed:
    print("FAILURES:")
    for f in _failed:
        print("  - " + f)
    sys.exit(1)
print("ALL GREEN")
