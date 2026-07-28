# Keep all generated files (.aux, .log, .pdf, etc.) in build/ instead of the repo root.
$out_dir = 'build';
$pdf_mode = 1;   # build PDF via pdflatex

# After every successful PDF build, structurally validate the output (async so
# it never slows the rebuild). Catches corrupt trailers that Preview still opens
# but resume checkers reject. See scripts/pdf_valid.py.
#
# --async always exits 0 for latexmk; the child prints [pdf-valid] ok/INVALID
# and writes build/<name>.pdf.INVALID on failure.
$success_cmd = 'python3 scripts/pdf_valid.py --async %D';
