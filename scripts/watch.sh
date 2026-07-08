#!/bin/bash
# Auto-rebuild every résumé variant whenever its .md changes.
# Started automatically by VSCode when this folder opens (see .vscode/tasks.json).
# Pipeline: resumes/X.md --md2tex.py--> resumes/X.tex --latexmk--> build/X.pdf
#
# Zero dependencies: polls each file's modification time once a second.
# Run manually with:  ./scripts/watch.sh   (from the repo root, or from anywhere)

cd "$(dirname "$0")/.." || exit 1   # repo root (this script lives in scripts/)
export PATH="/Library/TeX/texbin:$PATH"

build() {
  local md="$1" name
  name=$(basename "$md" .md)
  python3 scripts/md2tex.py "$md" "resumes/$name.tex" \
    && latexmk -pdf -interaction=nonstopmode "resumes/$name.tex"
}

echo "[resume watcher] initial build..."
mds=(resumes/*.md)
last=()
for i in "${!mds[@]}"; do
  build "${mds[$i]}"
  last[$i]=$(stat -f %m "${mds[$i]}" 2>/dev/null)
done

echo "[resume watcher] watching resumes/*.md — edit + save to rebuild (Ctrl-C to stop)"
while true; do
  sleep 1
  for i in "${!mds[@]}"; do
    md="${mds[$i]}"
    cur=$(stat -f %m "$md" 2>/dev/null)
    if [ "$cur" != "${last[$i]}" ]; then
      last[$i]="$cur"
      echo "[resume watcher] change detected in $md $(date '+%H:%M:%S'), rebuilding..."
      build "$md"
    fi
  done
done
