# Résumé

My résumé, written in **Markdown** and compiled to a polished one-page PDF through
LaTeX. Edit `resume.md`, save, and the PDF rebuilds itself — you never have to touch
the LaTeX.

```
resume.md  ──(md2tex.py)──▶  resume.tex  ──(latexmk)──▶  build/resume.pdf
```

## Quick start

```sh
# one-off build  ->  build/resume.pdf
python3 md2tex.py resume.md resume.tex && latexmk resume.tex

# or just edit resume.md in VSCode — see "Auto-rebuild" below
```

Requires a TeX distribution. On macOS:

```sh
brew install --cask mactex-no-gui     # provides latexmk + pdflatex at /Library/TeX/texbin
```

## Auto-rebuild (the intended workflow)

Open this folder in VSCode and a watcher starts automatically (`watch.sh`, wired up in
`.vscode/tasks.json` via `runOn: folderOpen`). Every time you save `resume.md`, it
regenerates the LaTeX and recompiles the PDF. The first time, VSCode asks to
**"Allow Automatic Tasks"** — allow it once.

Recommended layout: `resume.md` on the left, `build/resume.pdf` open in the
LaTeX Workshop viewer (auto-refreshes) on the right.

Run the watcher by hand instead: `./watch.sh` (zero dependencies — it polls the
file's mtime once a second).

## Markdown format

```
# Name                       -> centered name
- display | url              -> a contact link (one per line, under the name)

## Section                   -> a section heading
### a | b | c [| d]          -> an entry; field meaning depends on the section:
                                  Education          -> org | location | degree | dates
                                  Personal Projects  -> name | tech stack | [label](url)
                                  (anything else)    -> title | org | dates
                                                        (org may end with [label](url))
- bullet text                -> a résumé bullet; **bold** becomes \textbf{...}
: \rawlatex                  -> inject raw LaTeX here (e.g. `: \vspace{-12pt}`)
```

- Special characters (`& % $ # _ { } ~ ^ \`) are auto-escaped — write `React & Next`,
  `$5K`, `70%` naturally.
- The **Skills** section uses `- Label: a, b, c` bullets (no `###` entries).
- `[label](url)` anywhere a link is expected becomes a proper hyperlink.

## Files

| File | Purpose |
|------|---------|
| `resume.md` | **Source of truth.** Edit this. |
| `md2tex.py` | Markdown → LaTeX converter (preamble baked in; output matches `resume.tex` 1:1). |
| `resume.tex` | Generated LaTeX. Regenerated from `resume.md` on each build — don't edit by hand. |
| `resume-dirty.tex` | Full archive of alternate bullet phrasings, kept as LaTeX comments. |
| `watch.sh` | Zero-dependency file watcher that runs the build on save. |
| `test_md2tex.py` | Test suite for the converter (`python3 test_md2tex.py`). |
| `.vscode/tasks.json` | Auto-starts the watcher when the folder is opened. |
| `.latexmkrc` | Sends all build output to `build/`. |
| `build/` | Compiled PDF + aux files (gitignored). |

## Tests

```sh
python3 test_md2tex.py
```

Covers escaping, bold, links, field parsing, section dispatch, spacing directives, and
end-to-end LaTeX compilation of adversarial inputs.

## Credits

Built on the [Jake Gutierrez résumé template](https://github.com/sb2nov/resume) (MIT).
