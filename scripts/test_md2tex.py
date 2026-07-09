#!/usr/bin/env python3
"""Test suite for md2tex.py.

Covers unit behaviour (escaping, bold, links, field splitting, section dispatch,
directives) and end-to-end LaTeX compilation of adversarial inputs.

Run:  python3 test_md2tex.py
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("md2tex", os.path.join(HERE, "md2tex.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

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
        ok = r.returncode == 0 and os.path.exists(os.path.join(d, "t.pdf"))
        detail = ""
        if not ok:
            errs = [l for l in (r.stdout + r.stderr).splitlines()
                    if l.startswith("!") or "Error" in l or ".tex:" in l]
            detail = "\n        ".join(errs[:6]) or "(no pdf produced)"
        check("compile: " + label, ok, detail)


have_latexmk = subprocess.run(["bash", "-lc", "PATH=/Library/TeX/texbin:$PATH which latexmk"],
                              capture_output=True).returncode == 0
if not have_latexmk:
    print("[skip] latexmk not found -- skipping compilation tests")
else:
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

# ---------------------------------------------------------------- summary
print("\n" + "=" * 50)
print(f"PASSED {len(_passed)}   FAILED {len(_failed)}")
if _failed:
    print("FAILURES:")
    for f in _failed:
        print("  - " + f)
    sys.exit(1)
print("ALL GREEN")
