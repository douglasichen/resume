#!/usr/bin/env python3
"""Convert a simple Markdown resume into the project's LaTeX format.

Usage:
    python3 md2tex.py resume.md            # writes LaTeX to stdout
    python3 md2tex.py resume.md out.tex    # writes LaTeX to out.tex

Markdown schema
---------------
  # Name                         -> centered name
  - display | url                -> a contact link (one per line, under the name)

  ## Section                     -> \section{...}
  ### a | b | c [| d]            -> an entry header (field meaning depends on section)
  - bullet text                  -> a resume bullet (**bold** supported)
  : \rawlatex                    -> inject raw LaTeX at this point (e.g. \vspace{-12pt})

Section field meanings (by section title):
  Education          -> ### org | location | degree | dates
  Skills             -> - Label: comma, separated, values   (no ### entries)
  Personal Projects  -> ### name | tech stack | [label](url)
  everything else    -> ### title | org | dates             (org may end with [label](url))

Text is auto-escaped for LaTeX (& % $ # _) and **bold** becomes \textbf{...}.
The preamble and \end{document} are baked in verbatim, so output matches the
hand-written resume.tex layout.
"""
import sys, re

PREAMBLE = "\n\\documentclass[letterpaper,11pt]{article}\n\n\\usepackage{latexsym}\n\\usepackage[empty]{fullpage}\n\\usepackage{titlesec}\n\\usepackage{marvosym}\n\\usepackage[usenames,dvipsnames]{color}\n\\usepackage{verbatim}\n\\usepackage{enumitem}\n\\usepackage[hidelinks]{hyperref}\n\\usepackage{fancyhdr}\n\\usepackage[english]{babel}\n\\usepackage{tabularx}\n\\usepackage{graphicx}\n\\input{glyphtounicode}\n\n\\usepackage{eso-pic}\n\n\\usepackage{charter}\n\n\\pagestyle{fancy}\n\\fancyhf{} % clear all header and footer fields\n\\fancyfoot{}\n\\renewcommand{\\headrulewidth}{0pt}\n\\renewcommand{\\footrulewidth}{0pt}\n\n\\usepackage{graphicx}\n\\usepackage{fontawesome5}\n\\newcommand{\\externallink}[2]{%\n  \\href{#1}{#2\\,\\faExternalLink[regular]}%\n}\n\\newcommand{\\smallericon}[1]{\\texorpdfstring{\\scalebox{0.7}{#1}}{#1}}\n\n\\addtolength{\\oddsidemargin}{-0.5in}\n\\addtolength{\\evensidemargin}{-0.5in}\n\\addtolength{\\textwidth}{1.0in}\n\\addtolength{\\topmargin}{-.5in}\n\\addtolength{\\textheight}{1.0in}\n\n\\urlstyle{same}\n\n\\raggedbottom\n\\raggedright\n\\setlength{\\tabcolsep}{0in}\n\n\\titleformat{\\section}{\n  \\vspace{-6pt}\\scshape\\raggedright\\large\n}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]\n\n\\pdfgentounicode=1\n\n\\newcommand{\\resumeItem}[1]{\n  \\item\\small{\n    {#1 \\vspace{-0.6pt}}\n  }\n}\n\n\\newcommand{\\urlNewWindowLabel}[2]{\\href[pdfnewwindow=true]{#1}{#2}}\n\n\\newcommand{\\accomplishmentItem}[2]{\n  \\item\\small {\n    \\begin{tabular*}{0.94\\textwidth}{l@{\\extracolsep{\\fill}}r}\n      \\small#1 & #2 \\\\\n    \\end{tabular*}\\vspace{-7pt}\n  }\n}\n\n\\newcommand{\\resumeSubheading}[4]{\n  \\vspace{0pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & #2 \\\\\n      \\textit{\\small#3} & \\textit{\\small #4} \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeSubheadingD}[5]{\n  \\vspace{0pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & #2 \\\\\n      \\textit{\\small#3} & \\textit{\\small #4} \\\\\n    \\end{tabular*}\\vspace{-5pt}\n    \\begin{itemize}[leftmargin=*]\n      \\item \\small #5\n    \\end{itemize}\\vspace{-5pt}\n}\n\n\\newcommand{\\resumeSubheadingB}[3]{\n  \\vspace{0pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} $|$ \\textit{#3} & #2 \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\\newcommand{\\resumeSubheadingC}[4]{\n  \\vspace{0pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} $|$ \\textit{#3} $|$ \\textit{#4} & #2 \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeSubSubheading}[2]{\n    \\item\n    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}\n      \\textit{\\small#1} & \\textit{\\small #2} \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeProjectHeading}[2]{\n    \\item\n    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}\n      \\small#1 & #2 \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeSubItem}[1]{\\resumeItem{#1}\\vspace{-4pt}}\n\n\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}\n\n\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}\n\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}\n\\newcommand{\\resumeItemListStart}{\\begin{itemize}}\n\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-7pt}}\n\n\\begin{document}\n"
FOOTER = "\\end{document}\n"

LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# LaTeX special characters -> their escaped forms. Applied in a single pass over
# the source string so the backslashes/braces we insert are never re-escaped.
_SPECIALS = {
    '\\': r'\textbackslash{}',
    '{': r'\{', '}': r'\}',
    '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_',
    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
}


def esc(s):
    return ''.join(_SPECIALS.get(ch, ch) for ch in s)


def esc_url(u):
    """Escape the characters that break hyperref's \\href argument.

    Inside \\href, only # % & need a backslash (and they round-trip to the
    correct character in the link); everything else is fine verbatim.
    """
    return u.replace('#', r'\#').replace('%', r'\%').replace('&', r'\&')


def conv(s):
    """Escape LaTeX specials, then turn **bold** into \textbf{}."""
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', s)
    return s


def split_link(s):
    """Return (text_before_link, label, url). label/url are None if no link."""
    m = LINK.search(s)
    if not m:
        return s.strip(), None, None
    return s[:m.start()].strip(), m.group(1), m.group(2)


def fields(line):
    return [p.strip() for p in line.split('|')]


def parse(md):
    doc = {'name': '', 'contacts': [], 'sections': []}
    sec = entry = None
    in_header = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith('# '):
            doc['name'] = line[2:].strip()
            in_header, sec, entry = True, None, None
        elif line.startswith('## '):
            sec = {'title': line[3:].strip(), 'entries': [], 'bullets': []}
            doc['sections'].append(sec)
            entry, in_header = None, False
        elif line.startswith('### '):
            entry = {'header': line[4:].strip(), 'items': []}
            sec['entries'].append(entry)
        elif line.startswith(': '):
            if entry is not None:
                entry['items'].append(('raw', line[2:].strip()))
        elif line.startswith('- '):
            content = line[2:].strip()
            if in_header:
                doc['contacts'].append(content)
            elif entry is not None:
                entry['items'].append(('bullet', content))
            else:
                sec['bullets'].append(content)
    return doc


def emit_bullets(items):
    # A ': raw' directive after the last bullet is attached to the
    # \resumeItemListEnd line (e.g. \resumeItemListEnd\vspace{-10pt}); one that
    # sits between bullets is emitted inline inside the list.
    if not any(k == 'bullet' for k, _ in items):
        # No bullets at all (e.g. a bare ': \vspace{..}' after a Hackathon Wins
        # entry) -> emit directly, don't wrap an empty itemize (LaTeX errors on
        # \end{itemize} with no \item).
        return ['      ' + val for _, val in items]
    last_bullet = max((i for i, (k, _) in enumerate(items) if k == 'bullet'),
                      default=-1)
    inner, trailing = items[:last_bullet + 1], items[last_bullet + 1:]
    out = ['      \\resumeItemListStart']
    for kind, val in inner:
        if kind == 'bullet':
            out.append('        \\resumeItem{' + conv(val) + '}')
        else:
            out.append('        ' + val)
    end = '      \\resumeItemListEnd'
    for _, val in trailing:
        end += val
    out.append(end)
    return out


def emit_skills(bullets):
    out = ['\\section{Skills}',
           ' \\begin{itemize}[leftmargin=0.15in, label={}]',
           '    \\small{\\item{']
    rows = []
    for b in bullets:
        if ':' in b:
            label, vals = b.split(':', 1)
            rows.append('\\textbf{' + esc(label.strip()) + ':}{ ' + conv(vals.strip()) + '}')
        else:
            rows.append(conv(b))
    for i, r in enumerate(rows):
        suffix = ' \\\\' if i < len(rows) - 1 else ''
        prefix = '         ' if i == 0 else '     '
        out.append(prefix + r + suffix)
    out += ['    }}', ' \\end{itemize}']
    return out


def emit_entry(sectype, entry):
    f = fields(entry['header'])

    def g(i):
        return f[i] if i < len(f) else ''

    out = []
    if sectype == 'subheading':            # Education: org | loc | degree | dates
        out.append('    \\resumeSubheading')
        out.append('      {' + conv(g(0)) + '}{' + conv(g(1)) + '}')
        out.append('      {' + conv(g(2)) + '}{' + conv(g(3)) + '}')
    elif sectype == 'project':             # name | stack | [label](url)
        _, label, url = split_link(g(2))
        emph = conv(g(1))
        if url:
            emph += ' $|$ \\href{' + esc_url(url) + '}{{\\underline{' + conv(label) + '}}}'
        out.append('        \\resumeProjectHeading')
        out.append('          {\\textbf{' + conv(g(0)) + '} $|$ \\emph{' + emph + '}}{}')
    else:                                  # subheadingB: title | org | dates
        otext, label, url = split_link(g(1))
        if url:
            org = conv(otext) + ' $|$ \\underline{\\href{' + esc_url(url) + '}{' + conv(label) + '}}'
        else:
            org = conv(g(1))
        out.append('    \\resumeSubheadingB{' + conv(g(0)) + '}{' + conv(g(2)) + '}{' + org + '}')
    if entry['items']:
        out += emit_bullets(entry['items'])
    return out


def sectype_for(title):
    t = title.strip().lower()
    if t == 'education':
        return 'subheading'
    if t in ('personal projects', 'projects', 'hackathon wins', 'hackathons'):
        return 'project'
    if t == 'skills':
        return 'skills'
    return 'subheadingB'


def emit(doc):
    out = ['', '\\begin{center}',
           '    \\textbf{\\Huge ' + conv(doc['name']) + '} \\\\ \\vspace{1pt}']
    links = []
    for c in doc['contacts']:
        parts = [x.strip() for x in c.split('|', 1)]
        disp = parts[0]
        url = parts[1] if len(parts) > 1 else parts[0]
        links.append('    \\href{' + esc_url(url) + '}{\\underline{' + conv(disp) + '}}')
    for i, l in enumerate(links):
        out.append(l + (' $|$' if i < len(links) - 1 else ''))
    out += ['\\end{center}', '']
    for sec in doc['sections']:
        st = sectype_for(sec['title'])
        if st == 'skills':
            out += emit_skills(sec['bullets']) + ['']
            continue
        out.append('\\section{' + conv(sec['title']) + '}')
        out.append('  \\resumeSubHeadingListStart')
        for e in sec['entries']:
            out += emit_entry(st, e)
        out.append('  \\resumeSubHeadingListEnd')
        out.append('')
    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write('usage: md2tex.py resume.md [out.tex]\n')
        sys.exit(1)
    doc = parse(open(sys.argv[1]).read())
    tex = PREAMBLE + emit(doc) + FOOTER
    if len(sys.argv) > 2:
        open(sys.argv[2], 'w').write(tex)
    else:
        sys.stdout.write(tex)


if __name__ == '__main__':
    main()
