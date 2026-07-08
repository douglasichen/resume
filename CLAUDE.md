# Resume

A one-page LaTeX résumé generated from a simple Markdown source. Multiple **variants**
(e.g. general, quant-dev-targeted) live side by side in `resumes/`, each an independent
Markdown source built to its own PDF.

```
resumes/general.md       ──(scripts/md2tex.py)──▶  resumes/general.tex       ──(latexmk)──▶  build/general.pdf
resumes/quant-resume.md  ──(scripts/md2tex.py)──▶  resumes/quant-resume.tex  ──(latexmk)──▶  build/quant-resume.pdf
```

## Files

- **`resumes/*.md`** — source of truth, one file per variant. **Edit these.**
  `general.md` is the default/base résumé; `quant-resume.md` is retargeted for quant dev roles
  (leads with C++, math coursework, competitive programming; trims web/AI-agent framing).
- **`scripts/md2tex.py`** — converts a `resumes/*.md` → LaTeX. The preamble + macros are
  baked in; output is verified pixel-identical to the original hand-written resume.
- **`scripts/watch.sh`** — zero-dependency watcher: on any `resumes/*.md` save, runs
  `md2tex.py` + `latexmk` for that variant only.
- **`scripts/test_md2tex.py`** — test suite for the converter.
- **`resumes/*.tex`** — **generated** from the matching `resumes/*.md` on every build. Do
  **not** edit by hand; changes get overwritten on the next rebuild.
- **`resume-dirty.tex`** — archive of alternate bullet phrasings kept as LaTeX comments.
  Mine it for wording, then edit the relevant `resumes/*.md`.
- **`.vscode/tasks.json`** — auto-starts the watcher when the folder is opened.
- **`.latexmkrc`** — sends all build output into `build/`.
- **`media/`** — screenshots used in `README.md`.
- **`build/`** — compiled PDFs + aux files (gitignored), one PDF per variant, e.g.
  `build/general.pdf`, `build/quant-resume.pdf`.

## Workflow: edit Markdown, watch the PDF

Open this folder in VSCode and the watcher starts automatically (`watch.sh`, via
`.vscode/tasks.json` `runOn: folderOpen`). Edit any `resumes/*.md`, save, and its
`build/<variant>.pdf` rebuilds — no terminal needed. The first time, VSCode asks to
**"Allow Automatic Tasks"**; allow it once.

Recommended layout: `resumes/general.md` (or `resumes/quant-resume.md`) on the left,
`build/general.pdf` (LaTeX Workshop's viewer, which auto-refreshes) on the right. You
never touch the `.tex`.

Run the watcher by hand: `./scripts/watch.sh`. Stop the auto-start: delete `.vscode/tasks.json`.

## Build from the command line

Requires a TeX distribution (MacTeX); the engine lives at `/Library/TeX/texbin`.

```sh
python3 scripts/md2tex.py resumes/general.md resumes/general.tex && latexmk resumes/general.tex   # -> build/general.pdf
latexmk -c    # delete aux files in build/ (keep the PDFs)
latexmk -C    # delete everything generated, including the PDFs
```

If `latexmk` is "not found", MacTeX isn't on your PATH — restart the terminal, or:
`export PATH="/Library/TeX/texbin:$PATH"` (or `eval "$(/usr/libexec/path_helper)"`).

## Markdown schema

```
# Name                       -> centered name
- display | url              -> a contact link (one per line, under the name)

## Section                   -> \section{...}
### a | b | c [| d]          -> an entry; field meaning depends on the section:
       Education                          -> org | location | degree | dates
       Personal Projects / Hackathon Wins -> name | tech stack | [label](url)
       (anything else, e.g. Work, Leadership) -> title | org | dates
                                              (org may end with [label](url))
- bullet text                -> a résumé bullet; **bold** becomes \textbf{...}
: \rawlatex                  -> inject raw LaTeX here (e.g. `: \vspace{-12pt}`)
```

- Special characters (`& % $ # _ { } ~ ^ \`) are auto-escaped — write `React & Next`,
  `$5K`, `70%` naturally.
- The **Skills** section uses `- Label: a, b, c` bullets (no `###` entries).
- `[label](url)` becomes a hyperlink wherever a link is expected.
- A `: \vspace{..}` between bullets is inlined; after the last bullet it attaches to
  `\resumeItemListEnd` (preserves hand-tuned spacing).

## Tests

```sh
python3 scripts/test_md2tex.py
```

Covers escaping, bold, links, field parsing, section dispatch, spacing directives, and
end-to-end LaTeX compilation of adversarial inputs.

## Editing / template notes

- Keep it to **one page**. After editing, confirm `pdfinfo build/<variant>.pdf` still
  reports `Pages: 1`.
- Bullets must each fit on **one rendered line** — long bullets silently wrap. When in
  doubt, build and eyeball the PDF (or measure against the ~507pt line width).
- Based on the [Jake Gutierrez résumé template](https://github.com/sb2nov/resume) (MIT).
  Layout is driven by preamble macros (`\resumeSubheading`, `\resumeSubheadingB`,
  `\resumeProjectHeading`, `\resumeItem`); `md2tex.py` emits these for you.
- Packages used (`fontawesome5`, `charter`, `marvosym`, `hyperref`, `titlesec`,
  `enumitem`, …) all ship with MacTeX-full.

## Dependencies

Tested versions (nearby versions should work):

- **MacTeX (no GUI)** `2026.0324` — TeX Live 2026 (`latexmk` 4.88, `pdfTeX` 1.40.29):
  `brew install --cask mactex-no-gui`
- **Python** `3.10.17` (3.8+) — standard library only, no `pip install`
- **Bash** `5.2` (3.2+) — runs `scripts/watch.sh`
- **VSCode** `1.125.1` + **LaTeX Workshop** ext `james-yu.latex-workshop@10.16.1` —
  `code --install-extension james-yu.latex-workshop`
- **Poppler** (optional, dev only) — `pdfinfo`/`pdftoppm` for page-count & pixel checks:
  `brew install poppler`
