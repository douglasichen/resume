# Resume

LaTeX resume.

- **`resume.tex`** — the clean, primary resume. Edit this one.
- **`resume-dirty.tex`** — the full archive, same layout but with many alternate bullet
  phrasings kept around as comments. Mine it for wording, then port changes to `resume.tex`.

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
