# Resume

LaTeX resume.

- **`resume.md`** — simple Markdown source. The easiest place to edit content.
- **`resume.tex`** — the clean LaTeX resume (generated-compatible; safe to edit directly too).
- **`resume-dirty.tex`** — the full archive, same layout but with many alternate bullet
  phrasings kept around as comments. Mine it for wording, then port changes over.
- **`md2tex.py`** — converts `resume.md` -> LaTeX matching `resume.tex` 1:1.

All generated files (PDF + `.aux`/`.log`/etc.) go into `build/`, configured via
`.latexmkrc` (`$out_dir = 'build'`). The repo root stays clean — only `.tex` sources
live there. `build/` is gitignored.

The compiled PDFs are `build/resume.pdf` and `build/resume-dirty.pdf`.

### From the command line
Requires a TeX distribution (MacTeX). The engine lives at `/Library/TeX/texbin`.

```sh
# One-shot build -> build/resume.pdf
latexmk resume.tex

# Auto-rebuild on save while editing
latexmk -pvc resume.tex

# Delete aux files in build/ (keeps the PDF)
latexmk -c

# Delete everything generated, including the PDF
latexmk -C
```

If `latexmk` is "not found", the TeX binaries aren't on your PATH. Either restart the
terminal after installing MacTeX, or run:

```sh
eval "$(/usr/libexec/path_helper)"   # or: export PATH="/Library/TeX/texbin:$PATH"
```

### In VSCode (LaTeX Workshop)
The `LaTeX Workshop` extension (`james-yu.latex-workshop`) is configured in the user
`settings.json` to call `latexmk` by absolute path (so builds work regardless of how
VSCode was launched) and with `latex-workshop.latex.outDir` set to `%DIR%/build`, so
its output also lands in `build/`.

- Build: `Cmd+Option+B`
- Preview PDF: `Cmd+Option+V`
- It also builds automatically on save.

## Markdown pipeline (`resume.md` -> LaTeX)

`md2tex.py` turns a simple Markdown file into LaTeX that matches `resume.tex`
(verified pixel-identical). The LaTeX preamble + macros are baked into the script;
the Markdown only carries content.

```sh
python3 md2tex.py resume.md           # print LaTeX to stdout
python3 md2tex.py resume.md resume.tex  # regenerate resume.tex from resume.md
```

Markdown schema:

```
# Name                       -> centered name
- display | url              -> a contact link (one per line, under the name)

## Section                   -> \section{...}
### a | b | c [| d]          -> entry header; field meaning depends on the section:
                                  Education          -> org | location | degree | dates
                                  Personal Projects  -> name | tech stack | [label](url)
                                  (anything else)    -> title | org | dates
                                                        (org may end with [label](url))
- bullet text                -> a resume bullet; **bold** -> \textbf{...}
: \rawlatex                  -> inject raw LaTeX here (e.g. : \vspace{-12pt})
```

Special characters (`& % $ # _`) are auto-escaped, so write `React & Next`, `$5K`,
`70%` naturally. The **Skills** section uses `- Label: a, b, c` bullets (no `###`).
A `: \vspace{..}` placed between bullets is inlined; placed after the last bullet it
attaches to `\resumeItemListEnd` (matches the hand-tuned spacing in the original).

### Auto-rebuild (edit Markdown, watch the PDF)

Opening this folder in VSCode auto-starts a watcher (`watch.sh`, wired up in
`.vscode/tasks.json` with `runOn: folderOpen`). It rebuilds `build/resume.pdf`
every time `resume.md` is saved — no terminal needed. The first time, VSCode asks
to "Allow Automatic Tasks"; allow it once.

Recommended layout: `resume.md` on the left, `build/resume.pdf` (LaTeX Workshop's
viewer, which auto-refreshes) on the right. You never need to touch the `.tex`.

The watcher is zero-dependency (polls the file's mtime once a second). To run it
by hand instead: `./watch.sh`. To stop the auto-start, delete `.vscode/tasks.json`.

## Editing notes

- This is the [Jake Gutierrez resume template](https://github.com/sb2nov/resume) (MIT).
- Layout is driven by custom macros defined in the preamble — prefer using them over
  raw LaTeX so spacing stays consistent:
  - `\resumeSubheading{title}{date}{subtitle}{location}` — dated role/education entry
  - `\resumeSubheadingB{title}{date}{org}` — single-line role with `org` after a `|`
  - `\resumeProjectHeading{heading}{date}` — project entry
  - `\resumeItem{...}` — a bullet (wrap groups in `\resumeItemListStart` / `...End`)
- `resume-dirty.tex` keeps a lot of content commented out (`%`) — an archive of
  alternate bullet phrasings. `resume.tex` has those stripped for a clean source.
- Packages in use include `fontawesome5`, `charter` (font), `marvosym`, `hyperref`,
  `titlesec`, `enumitem`. All ship with MacTeX-full.
- Keep it to **one page**. After editing, rebuild and confirm `pdfinfo resume.pdf`
  still reports `Pages: 1`.

## Dependencies

- MacTeX (full): `brew install --cask mactex-no-gui`
- VSCode extension: `james-yu.latex-workshop`
