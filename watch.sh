#!/bin/bash
# Auto-rebuild the resume whenever resume.md changes.
# Started automatically by VSCode when this folder opens (see .vscode/tasks.json).
# Pipeline: resume.md --md2tex.py--> resume.tex --latexmk--> build/resume.pdf
#
# Zero dependencies: polls the file's modification time once a second.
# Run manually with:  ./watch.sh

cd "$(dirname "$0")" || exit 1
export PATH="/Library/TeX/texbin:$PATH"

build() {
  python3 md2tex.py resume.md resume.tex \
    && latexmk -pdf -interaction=nonstopmode resume.tex
}

echo "[resume watcher] initial build..."
build

last=$(stat -f %m resume.md 2>/dev/null)
echo "[resume watcher] watching resume.md — edit + save to rebuild (Ctrl-C to stop)"
while true; do
  sleep 1
  cur=$(stat -f %m resume.md 2>/dev/null)
  if [ "$cur" != "$last" ]; then
    last="$cur"
    echo "[resume watcher] change detected $(date '+%H:%M:%S'), rebuilding..."
    build
  fi
done
