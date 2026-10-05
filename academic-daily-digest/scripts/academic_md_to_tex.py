#!/usr/bin/env python3
"""academic_md_to_tex.py — 学术日报 Markdown → 学术气质 PDF（XeLaTeX）。
用法: python3 academic_md_to_tex.py <input.md> <output.pdf>

支持的存档 Markdown 结构（academic-daily-digest skill）：
  # 学术文献日报 YYYY-MM-DD ...          → 文档标题（取日期）
  ## ⭐ 今日必读 / ## 🔬 核心方向 ...     → 节
  条目（两种）：
    1. **标题** (Venue) — 摘要...        （必读，编号）
       🔗 url
    - **Venue** | 标题 — 摘要...          （普通，期刊打头）
       🔗 url
  尾部： 共处理 N 条 / 信源异常：...
"""
import re, sys, subprocess, os, tempfile, shutil, datetime

# ---------------- 解析 ----------------

def strip_md(s):
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    return s.strip()

def parse(md):
    lines = md.splitlines()
    meta = {'date': '', 'count': '', 'notes': ''}
    sections = []   # [(title, [entry])]
    cur = None
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if not cur and ln.startswith('# '):
            d = re.search(r'(\d{4}-\d{2}-\d{2})', ln)
            if d:
                meta['date'] = d.group(1)
            i += 1
            continue
        m = re.match(r'^##(?!#)\s+(.+?)\s*$', ln)
        if m:
            cur = (strip_md(m.group(1)), [])
            sections.append(cur)
            i += 1
            continue
        # ### 条目（新存档格式）: ### 1. Title [NN/100] 或 ### Title [NN/100]
        m = re.match(r'^#{3}\s+(?:(\d+)[.)]\s+)?(.+?)\s*(?:\[(\d+)\s*/\s*100\])?\s*$', ln)
        if m and cur is not None:
            num = m.group(1)
            title = strip_md(m.group(2))
            score = m.group(3)
            link = ''
            desc_parts = []
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if re.match(r'^#{1,3}\s', l2):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link = lm.group(1).strip()
                elif l2 and not l2.startswith('来源：'):
                    desc_parts.append(l2)
                i += 1
            desc = strip_md(' '.join(desc_parts))
            tail = ('（评分 ' + score + '）') if score else ''
            cur[1].append({'num': num, 'org': '', 'title': title + tail,
                           'desc': desc, 'link': link})
            continue
        # 编号条目（必读）: 1. **Title** (Venue) — desc
        m = re.match(r'^(\d+)[.)]\s+\*\*(.+?)\*\*\s*(.*)$', ln)
        if m and cur is not None:
            num = m.group(1)
            title = strip_md(m.group(2))
            rest = m.group(3)
            vm = re.match(r'^[\(（]([^)）]+)[\)）]\s*(?:[—–-]\s*)?(.*)$', rest)
            venue, desc = '', ''
            if vm:
                venue = vm.group(1).strip()
                desc = vm.group(2).strip()
            else:
                dm = re.match(r'^[—–-]\s*(.*)$', rest)
                if dm:
                    desc = dm.group(1).strip()
            link = ''
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if re.match(r'^#{2,3}\s', l2) or re.match(r'^(?:\d+[.)]|[-*])\s+\*\*', l2):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link = lm.group(1).strip()
                elif l2:
                    desc = (desc + ' ' + l2).strip()
                i += 1
            cur[1].append({'num': num, 'org': venue, 'title': title,
                           'desc': strip_md(desc), 'link': link})
            continue
        # 期刊条目: - **Venue** | Title — desc   或  - **Venue** | Title
        m = re.match(r'^[-*]\s+\*\*(.+?)\*\*\s*(.*)$', ln)
        if m and cur is not None:
            org = m.group(1).strip()
            rest = m.group(2).strip()
            title, desc = rest, ''
            tm = re.match(r'^[|｜]\s*(.+)$', rest)
            if tm:
                rest2 = tm.group(1).strip()
                dm = re.match(r'^(.+?)\s*[—–-]\s*(.+)$', rest2)
                if dm:
                    title, desc = dm.group(1).strip(), dm.group(2).strip()
                else:
                    title = rest2
            link = ''
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if re.match(r'^#{2,3}\s', l2) or re.match(r'^(?:\d+[.)]|[-*])\s+\*\*', l2):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link = lm.group(1).strip()
                elif l2:
                    desc = (desc + ' ' + l2).strip()
                i += 1
            title = strip_md(title)
            desc = strip_md(desc)
            desc = re.sub(r'^见必读[。；.]?\s*', '', desc)
            cur[1].append({'num': None, 'org': org, 'title': title,
                           'desc': desc, 'link': link})
            continue
        i += 1
    mc = re.search(r'共处理\s*(\d+)\s*条', md)
    if mc:
        meta['count'] = mc.group(1)
    mn = re.search(r'信源异常[：:]\s*(.+)', md)
    if mn:
        meta['notes'] = mn.group(1).strip()
    return sections, meta

# ---------------- LaTeX ----------------

_ESC = [('\\', r'\textbackslash{}'), ('&', r'\&'), ('%', r'\%'), ('$', r'\$'),
        ('#', r'\#'), ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
        ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')]

def esc(s):
    if not s:
        return ''
    for a, b in _ESC:
        s = s.replace(a, b)
    return s

def esc_url(s):
    return s.replace('%', r'\%').replace('#', r'\#') \
            .replace('&', r'\&').replace('_', r'\_').replace('~', r'\textasciitilde{}')

PREAMBLE = r"""% !TEX program = xelatex
\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.3cm,top=2.8cm,bottom=2.8cm]{geometry}
\usepackage[UTF8]{ctex}
\setCJKmainfont{Noto Serif CJK SC}
\setCJKsansfont{Noto Sans CJK SC}
\setmainfont{DejaVu Serif}
\usepackage{xcolor}
\definecolor{inkblue}{HTML}{163A66}
\definecolor{accent}{HTML}{2B6CB0}
\definecolor{softgray}{HTML}{64748B}
\definecolor{rulegray}{HTML}{CBD5E0}
\definecolor{bgsoft}{HTML}{F5F8FC}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage[colorlinks=true,linkcolor=accent,urlcolor=accent,citecolor=accent]{hyperref}
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable}

\titleformat{\section}{\large\bfseries\sffamily\color{inkblue}}{}{0pt}{}[\vspace{-0.55em}{\color{accent}\rule{\textwidth}{1.1pt}}]
\titlespacing*{\section}{0pt}{1.25em}{0.75em}
\setlist[itemize]{leftmargin=1.35em,itemsep=0.6em,topsep=0.35em,parsep=0.1em}
\setlist[enumerate]{leftmargin=1.75em,itemsep=0.65em,topsep=0.35em,parsep=0.1em}

\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small\sffamily\color{inkblue}\textbf{学术文献日报}}
\fancyhead[R]{\small\sffamily\color{softgray}@@DATE@@}
\fancyfoot[C]{\small\color{softgray}\thepage\,/\,\pageref{LastPage}}
\renewcommand{\headrulewidth}{0.35pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{rulegray}\leaders\hrule height \headrulewidth\hfill}}
\linespread{1.16}
"""

TITLEBLOCK = r"""
\begin{center}
{\fontsize{25}{30}\selectfont\sffamily\bfseries\color{inkblue} 学术文献日报}\\[0.55em]
{\large\color{accent}@@DATE@@}\\[0.75em]
{\color{rulegray}\rule{0.66\textwidth}{0.7pt}}
\end{center}
\vspace{0.35em}
"""

def entry_tex(e):
    out = []
    head = esc(e['title'])
    if e.get('org'):
        head += r"\quad{\small\color{softgray}[" + esc(e['org']) + "]}"
    out.append(r"\item \textbf{" + head + r"}\par")
    if e['desc']:
        out.append(r"\vspace{0.12em}" + esc(e['desc']) + r"\par")
    if e['link']:
        u = esc_url(e['link'])
        out.append(r"\vspace{0.15em}{\small\color{softgray}$\triangleright$ \url{" + u + r"}}\par")
    return '\n'.join(out)

def build(md, out_pdf):
    sections, meta = parse(md)
    if not meta['date']:
        meta['date'] = datetime.date.today().isoformat()
    try:
        d = datetime.date.fromisoformat(meta['date'])
        date_cn = "{} 年 {} 月 {} 日".format(d.year, d.month, d.day)
    except ValueError:
        date_cn = meta['date']

    parts = [PREAMBLE.replace('@@DATE@@', esc(date_cn)), "\\begin{document}\n",
             TITLEBLOCK.replace('@@DATE@@', esc(date_cn))]

    for title, entries in sections:
        if not entries:
            continue
        clean = re.sub(r'^[^\w\u4e00-\u9fff（(★]+', '', title).strip()
        clean = re.sub(r'^必读', '今日必读', clean)
        parts.append("\n\\section*{" + esc(clean) + "}\n")
        numbered = bool(entries[0].get('num'))
        if numbered:
            label = r"\textbf{\color{accent}\arabic*.}"
            parts.append("\\begin{enumerate}[label={" + label + "},labelsep=0.45em]\n")
        else:
            parts.append("\\begin{itemize}\n")
        for e in entries:
            parts.append(entry_tex(e) + '\n')
        parts.append("\\end{enumerate}\n" if numbered else "\\end{itemize}\n")

    if meta['notes']:
        parts.append("\n\\vspace{0.9em}\n\\begin{tcolorbox}[colback=bgsoft,colframe=rulegray,"
                     "boxrule=0.3pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt]\n"
                     "{\\small\\color{softgray}信源异常：" + esc(meta['notes']) + "}\n"
                     "\\end{tcolorbox}\n")

    count = "共收录 {} 条文献".format(meta['count']) if meta['count'] else ""
    parts.append("\n\\vfill\n\\begin{center}\n{\\small\\color{softgray} " + esc(count) +
                 " \\quad·\\quad 由 Hermes 学术订阅流水线自动生成}\n\\end{center}\n\\end{document}\n")

    tex = ''.join(parts)
    with tempfile.TemporaryDirectory() as td:
        texf = os.path.join(td, 'digest.tex')
        with open(texf, 'w') as f:
            f.write(tex)
        r = None
        for _ in range(2):
            r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                                '-output-directory', td, texf],
                               capture_output=True, text=True, timeout=240)
        pdf = os.path.join(td, 'digest.pdf')
        if os.path.exists(pdf):
            shutil.copy(pdf, out_pdf)
            with open(os.path.splitext(out_pdf)[0] + '.tex', 'w') as f:
                f.write(tex)
            return True, tex
        log = (r.stdout or '')[-4000:] + '\n---STDERR---\n' + (r.stderr or '')[-1500:]
        return False, log

if __name__ == '__main__':
    md = open(sys.argv[1], encoding='utf-8').read()
    ok, info = build(md, sys.argv[2])
    print('BUILD_OK' if ok else 'BUILD_FAIL')
    if not ok:
        print(info)
