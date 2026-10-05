#!/usr/bin/env python3
"""digest_to_mobile_pdf.py — 日报 Markdown → 手机图文卡片 PDF（Chromium 打印）。
用法: python3 digest_to_mobile_pdf.py <input.md> <output.pdf> [--style news|academic] [--title 自定义标题]

两条产品线共用：
  --style news     AI 热点日报（📡 橙蓝主题，快讯用紧凑条）
  --style academic 学术文献日报（🧪 深蓝主题，评分徽章）

支持的存档 Markdown（两种条目格式自动识别）：
  ## 节标题
  ### N. 标题 [NN/100]   /  ### 标题 [NN/100]
  摘要文字行…
  🔗 https://…
  或
  - **Venue** | 标题 — 摘要
    🔗 https://…
尾部：共处理 N 条 / 信源异常：… 会被解析为页脚。
"""
import re, sys, os, subprocess, tempfile, shutil, argparse, datetime, html

# Chromium path: set CHROME env var, or auto-detect playwright/standalone installs
import glob
CHROME = os.environ.get('CHROME') or next(
    (p for pat in (
        os.path.expanduser('~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell'),
        os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux/chrome'),
    ) for p in sorted(glob.glob(pat), reverse=True)),
    'chrome-headless-shell')

# ---------- 解析（与 LaTeX 版同样的规则） ----------

def strip_md(s):
    return re.sub(r'\*\*(.+?)\*\*', r'\1', s).strip()

def parse(md):
    lines = md.splitlines()
    meta = {'date': '', 'count': '', 'notes': '', 'h1': ''}
    sections = []
    cur = None
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith('# ') and not meta['h1']:
            meta['h1'] = strip_md(ln[2:])
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
        # 日报头条格式: **N. 标题**（热度 ★n ｜ 分数 NN ｜ 来源们）
        m = re.match(r'^\*\*(\d+)[.、]\s*(.+?)\*\*\s*[（(](.+?)[)）]\s*$', ln)
        if m and cur is not None:
            num, title, tail = m.group(1), strip_md(m.group(2)), m.group(3)
            score = None
            sm = re.search(r'分数\s*(\d+)', tail)
            if sm:
                score = sm.group(1)
            srcs = ''
            scm = re.search(r'[｜|]\s*([^｜|]+)$', tail)
            if scm:
                srcs = scm.group(1).strip()
            desc, link = [], ''
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if (re.match(r'^#{1,3}\s', l2) or re.match(r'^\*\*\d+[.、]', l2)
                        or l2.startswith('---') or l2.startswith('## ')):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link = lm.group(1).strip()
                elif l2 and not l2.startswith('推荐理由：'):
                    desc.append(strip_md(l2))
                i += 1
            cur[1].append({'num': num, 'org': srcs, 'title': title,
                           'score': score, 'desc': strip_md(' '.join(desc)), 'link': link})
            continue
        m = re.match(r'^#{3}\s+(?:(\d+)[.)]\s+)?(.+?)\s*(?:\[(\d+)\s*/\s*100\])?\s*$', ln)
        if m and cur is not None:
            num, title, score = m.group(1), strip_md(m.group(2)), m.group(3)
            link, desc = '', []
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if re.match(r'^#{1,3}\s', l2):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link = lm.group(1).strip()
                elif l2 and not l2.startswith('来源：'):
                    desc.append(l2)
                i += 1
            cur[1].append({'num': num, 'org': '', 'title': title,
                           'score': score, 'desc': strip_md(' '.join(desc)), 'link': link})
            continue
        m = re.match(r'^[-*]\s+\*\*(.+?)\*\*\s*(.*)$', ln)
        if m and cur is not None:
            org = m.group(1).strip()
            rest = m.group(2).strip()
            title, desc = rest, ''
            tm = re.match(r'^[|｜]\s*(.+)$', rest)
            if tm:
                rest2 = tm.group(1).strip()
                dm = re.match(r'^(.+?)\s*[—–-]\s*(.+)$', rest2)
                title, desc = (dm.group(1).strip(), dm.group(2).strip()) if dm else (rest2, '')
            link = []
            i += 1
            while i < len(lines):
                l2 = lines[i].strip()
                if re.match(r'^#{1,3}\s', l2) or re.match(r'^[-*]\s+\*\*', l2):
                    break
                lm = re.match(r'^🔗\s*(\S+)', l2)
                if lm:
                    link.append(lm.group(1).strip())
                elif l2:
                    desc = (desc + ' ' + l2).strip()
                i += 1
            title = strip_md(title)
            desc = re.sub(r'^见必读[。；.]?\s*', '', strip_md(desc))
            cur[1].append({'num': None, 'org': org, 'title': title,
                           'score': None, 'desc': desc, 'link': link[0] if link else ''})
            continue
        i += 1
    mc = re.search(r'共处理[约]?\s*(\d+)\s*条', md)
    if mc:
        meta['count'] = mc.group(1)
    mn = re.search(r'信源异常[：:]\s*(.+)', md)
    if mn:
        meta['notes'] = mn.group(1).strip()
    return sections, meta

# ---------- HTML 生成 ----------

CSS_COMMON = """
@page { size: 100mm 178mm; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; padding: 7mm 6mm 9mm; font-family: 'Noto Sans CJK SC', 'Noto Color Emoji', sans-serif;
       font-size: 10.2px; line-height: 1.58; color: #1e293b; background: #fff; }
.card { overflow: hidden; }
.masthead { text-align: center; margin: 1mm 0 4mm; }
.masthead .t { font-size: 21px; font-weight: 800; letter-spacing: .05em; }
.masthead .d { font-size: 10.5px; margin-top: 1.5mm; color: var(--accent); font-weight: 600; }
.masthead .rule { width: 56%; height: 2.5px; margin: 2.5mm auto 0; background: var(--accent); border-radius: 2px; opacity: .85; }
h2.sec { font-size: 13.5px; font-weight: 800; color: var(--accent); margin: 5.5mm 0 2.5mm;
         padding-bottom: 1.2mm; border-bottom: 2px solid var(--accent); }
.cardwrap { break-inside: avoid; page-break-inside: avoid; margin: 0 0 2.8mm; padding-top: 2.5mm; }
.cardwrap:first-child { padding-top: 0; }
.card { background: var(--cardbg); border-radius: 3mm; padding: 2.8mm 3.2mm;
        border-left: 1.2mm solid var(--accent); break-inside: avoid; page-break-inside: avoid; }
h2.sec { break-after: avoid; page-break-after: avoid; }
.card .hd { display: flex; align-items: flex-start; gap: 2mm; }
.badge { flex: 0 0 auto; min-width: 5.4mm; height: 5.4mm; border-radius: 50%; background: var(--accent);
         color: #fff; font-size: 9.5px; font-weight: 800; text-align: center; line-height: 5.4mm; margin-top: .3mm; }
.card.plain .badge { border-radius: 1.2mm; }
.card .tt { font-weight: 800; font-size: 11px; line-height: 1.45; }
.card .ds { margin-top: 1.2mm; color: #334155; }
.card .lk { margin-top: 1.2mm; font-size: 9px; }
.card .lk a { color: var(--accent); text-decoration: none; word-break: break-all; }
.hero { margin-top: 1.8mm; border-radius: 2.2mm; overflow: hidden; background: #fff;
        border: 1px solid #e2e8f0; break-inside: avoid; text-align: center; }
.hero img { display: block; width: 100%; height: auto; max-height: 42mm; object-fit: contain; }
.score { display: inline-block; background: var(--accent); color: #fff; border-radius: 1mm;
         font-size: 8.5px; font-weight: 800; padding: 0 1.6mm; margin-left: 1.5mm; vertical-align: 1px; }
.org { display: inline-block; color: var(--accent); font-weight: 700; font-size: 9px; margin-left: 1.5mm; }
.foot { margin-top: 5mm; padding-top: 2.5mm; border-top: 1px solid #e2e8f0;
        font-size: 8.8px; color: #94a3b8; text-align: center; }
.foot a { color: #94a3b8; }
.notes { background: #FFF7ED; border: 1px solid #FDBA74; border-radius: 2mm; padding: 2.2mm 3mm;
         font-size: 9px; color: #9A3412; margin-top: 4mm; }
"""

STYLE_THEMES = {
    'academic': """
      :root { --accent: #1d4ed8; --cardbg: #F0F6FF; }
      .masthead .t { color: #16324f; }
    """,
    'news': """
      :root { --accent: #ea580c; --cardbg: #FFF7F2; }
      .masthead .t { color: #7c2d12; }
      h2.sec { color: #c2410c; border-color: #f97316; }
      .card { border-left-color: #f97316; }
      .badge { background: #ea580c; }
      .score { background: #ea580c; }
    """,
}

def esc(s):
    return html.escape(s or '', quote=False)

def build_html(sections, meta, style, title_override=None, hero_map=None):
    title = title_override or ('学术文献日报' if style == 'academic' else 'AI 热点日报')
    if not meta['date']:
        meta['date'] = datetime.date.today().isoformat()
    try:
        d = datetime.date.fromisoformat(meta['date'])
        date_cn = "{} 年 {} 月 {} 日".format(d.year, d.month, d.day)
    except ValueError:
        date_cn = meta['date']
    h = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>',
         CSS_COMMON, STYLE_THEMES[style], '</style></head><body>']
    h.append('<div class="masthead"><div class="t">{}</div><div class="d">{}</div><div class="rule"></div></div>'
             .format(esc(title), esc(date_cn)))
    seq = 0        # 全局连续序号，不管存档里是否缺号
    for sec_title, entries in sections:
        if not entries:
            continue
        clean = re.sub(r'^[^\w\u4e00-\u9fff（(★⭐🔬🛠🌍👀🔥📌⚡]+', '', sec_title).strip()
        h.append('<h2 class="sec">{}</h2>'.format(esc(clean)))
        for e in entries:
            seq += 1
            num = str(seq)
            tt = '<div class="tt">{}{}'.format(esc(e['title']),
                 '<span class="score">{}/100</span>'.format(e['score']) if e.get('score') else '')
            if e.get('org'):
                tt += '<span class="org">{}</span>'.format(esc(e['org']))
            tt += '</div>'
            ds = '<div class="ds">{}</div>'.format(esc(e['desc'])) if e['desc'] else ''
            lk = '<div class="lk"><a href="{}">🔗 {}</a></div>'.format(esc(e['link']), esc(e['link'])) if e.get('link') else ''
            hero = ''
            if hero_map:
                img = hero_map.get(num) or hero_map.get(e.get('num') or '')
                if img and not img.endswith('.svg'):   # 只有真图才放；抓不到就不放图
                    hero = '<div class="hero"><img src="file://{}"></div>'.format(img)
            h.append('<div class="cardwrap"><div class="card"><div class="hd"><div class="badge">{}</div>{}</div>{}{}{}</div></div>'.format(
                esc(num), tt, ds, hero, lk))
    if meta['notes']:
        h.append('<div class="notes">⚠ 信源异常：{}</div>'.format(esc(meta['notes'])))
    foot = '共处理 {} 条'.format(meta['count']) if meta['count'] else ''
    h.append('<div class="foot">{} ·· 由 Hermes 订阅流水线生成 ··</div>'
             .format(esc(foot)))
    h.append('</body></html>')
    return '\n'.join(h)

def md_to_pdf(md_path, pdf_path, style, title=None, hero=True, hero_dir=None):
    md = open(md_path, encoding='utf-8').read()
    sections, meta = parse(md)
    hero_map = None
    if hero:
        try:
            items = []
            seq = 0
            for _, entries in sections:
                for e in entries:
                    seq += 1
                    items.append({'key': str(seq), 'link': e.get('link') or '',
                                  'title': e.get('title', ''),
                                  'org': e.get('org', '') or 'Digest'})
            if items:
                hd = hero_dir or tempfile.mkdtemp(prefix='heros_')
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import fetch_hero_images as FH
                hero_map = FH.fetch_all(items, hd,
                                        '#1d4ed8' if style == 'academic' else '#ea580c')
        except Exception as ex:
            print('hero fetch failed (fallback to text-only):', ex)
            hero_map = None
    html_str = build_html(sections, meta, style, title, hero_map)
    with tempfile.TemporaryDirectory() as td:
        hf = os.path.join(td, 'digest.html')
        with open(hf, 'w', encoding='utf-8') as f:
            f.write(html_str)
        r = subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-sandbox',
                            '--no-pdf-header-footer', '--virtual-time-budget=8000',
                            '--print-to-pdf=' + pdf_path, hf],
                           capture_output=True, text=True, timeout=180)
        ok = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000
        with open(os.path.splitext(pdf_path)[0] + '.html', 'w', encoding='utf-8') as f:
            f.write(html_str)
        return ok, (r.stderr or '')[-1200:]

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--style', default='academic', choices=['news', 'academic'])
    ap.add_argument('--title', default=None)
    ap.add_argument('--no-hero', action='store_true', help='不抓主图（纯文本卡片）')
    ap.add_argument('--hero-dir', default=None)
    a = ap.parse_args()
    ok, err = md_to_pdf(a.input, a.output, a.style, a.title,
                        hero=not a.no_hero, hero_dir=a.hero_dir)
    print('BUILD_OK' if ok else 'BUILD_FAIL')
    if not ok:
        print(err)
