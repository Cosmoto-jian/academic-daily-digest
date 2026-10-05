#!/usr/bin/env python3
"""fetch_hero_images.py — 为日报每条条目抓取主图。
用法: python3 fetch_hero_images.py <items_json> <outdir>
  items_json: [{"key": "1", "link": "https://...", "title": "...", "org": "..."}]
  输出: 写出图片到 outdir，打印 JSON: {"1": "/abs/path.png", ...}

策略（按优先级）：
  arXiv abs/html → html 版第一张内容图（teaser）
  nature.com → twitter:image
  其他网页 → og:image / twitter:image / 第一张候选内容图
  失败 → 生成主题色 SVG 占位图（含来源/期刊缩写），保证每条都有图
"""
import sys, os, json, re, hashlib, subprocess, urllib.parse

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
MIN_BYTES = 6000
SKIP_HINT = re.compile(r'logo|icon|avatar|sprite|placeholder|spacer|pixel|badge|qrcode|wechat|weibo|advert|banner_s|/ads?/', re.I)


def curl(url, out=None, extra=None, timeout=20):
    cmd = ['curl', '-sL', '--max-time', str(timeout), '-A', UA,
           '-H', 'Accept: text/html,image/*,*/*']
    if out:
        cmd += ['-o', out, '-w', '%{http_code} %{size_download} %{content_type}']
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    return r.stdout.strip(), (r.returncode == 0)


def page_html(url):
    body, ok = curl(url, timeout=28)
    # arXiv 长文偶尔 rc=28（截断）但已有完整 HTML：以内容长度为准
    if len(body) > 20000:
        return body
    return body if ok else ''


def meta_image(html):
    """从页面 HTML 提取 og:image / twitter:image（含相对路径）。"""
    for pat in (r'<meta[^>]+(?:property|name)=["\'](?:og:image|og:image:secure_url|twitter:image)["\'][^>]*>',
                r'<meta[^>]+content=["\'][^"\']+["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*>'):
        for tag in re.findall(pat, html, re.I):
            m = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
            if m:
                return m.group(1)
    return ''


def content_images(html, base_url):
    """页面里像内容的图：优先 <figure> 内的图，再退回全文扫描；排除 logo/icon/小图/极端长宽比。"""
    def pick(scope_html):
        out = []
        for tag in re.findall(r'<img[^>]+>', scope_html, re.I):
            src = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
            if not src:
                continue
            u = src.group(1).strip()
            if not u or u.startswith('data:'):
                continue
            if SKIP_HINT.search(u) or '/static/' in u:
                continue
            alt = re.search(r'alt=["\']([^"\']*)["\']', tag, re.I)
            if alt and re.search(r'logo|icon|badge|sponsor|foundation', alt.group(1), re.I):
                continue
            if re.search(r'(?:class|id)=["\'][^"\']*(?:logo|icon|sponsor|footer|header|nav)[^"\']*["\']',
                         tag, re.I):
                continue
            w = re.search(r'width=["\'](\d+)["\']', tag, re.I)
            h = re.search(r'height=["\'](\d+)["\']', tag, re.I)
            wi = int(w.group(1)) if w else 0
            hi = int(h.group(1)) if h else 0
            if wi and wi < 260:
                continue
            if hi and hi < 140:
                continue
            # 极端长宽比（横幅 logo 特征）
            if wi and hi and (wi / max(hi, 1) > 2.6 or hi / max(wi, 1) > 2.6):
                continue
            if not re.search(r'\.(png|jpe?g|webp|gif)(\?|$)', u, re.I):
                continue
            out.append(urllib.parse.urljoin(base_url, u))
        return out

    # 1) 优先 arXiv LaTeXML 的 figure 区块 / 标准 <figure>
    for pat in (r'<figure[^>]*>(.*?)</figure>', r'<div[^>]+class="[^"]*ltx_figure[^"]*"[^>]*>(.*?)</div>'):
        for block in re.findall(pat, html, re.I | re.S):
            found = pick(block)
            if found:
                return found
    # 2) 正文容器（排除 header/nav/footer 区块）
    for pat in (r'<article[^>]*>(.*?)</article>', r'<main[^>]*>(.*?)</main>'):
        for block in re.findall(pat, html, re.I | re.S):
            found = pick(block)
            if found:
                return found
    # 3) 全文兜底
    return pick(html)


def arxiv_html_image(abs_link):
    """arXiv HTML 版：正文图都在 /html/{id}v{n}/ 下，用路径白名单而不是 figure 检测。"""
    m = re.search(r'arxiv\.org/abs/([\w.\-/]+)', abs_link)
    if not m:
        return ''
    aid = m.group(1)
    for suffix in ('v1', 'v2', 'v3', ''):
        base = 'https://arxiv.org/html/{}{}'.format(aid, suffix)
        html = page_html(base + '/')
        if not html or len(html) < 5000:
            html = page_html(base)
        if not html or 'No HTML' in html[:5000] or len(html) < 5000:
            continue
        best = ''
        for tag in re.findall(r'<img[^>]+>', html, re.I):
            src = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
            if not src:
                continue
            u = src.group(1).strip()
            if not re.search(r'\.(png|jpe?g|webp)(\?|$)', u, re.I):
                continue
            # arXiv 正文图形态: "{id}v{n}/xxx.png"（相对 /html/ 目录）
            if re.match(r'^[\w.\-]+/[\w.\-%]+\.(png|jpe?g|webp)$', u) and aid.split('v')[0] in u:
                full = 'https://arxiv.org/html/' + u
            elif re.match(r'^[\w.\-%]+\.(png|jpe?g|webp)$', u):
                full = urllib.parse.urljoin(base + '/', u)
            else:
                continue
            if re.search(r'logo|icon|glyph|banner|badge', u, re.I):
                continue
            w = re.search(r'width=["\'](\d+)["\']', tag, re.I)
            if w and int(w.group(1)) < 200:
                continue
            # teaser / fig1 优先
            if re.search(r'teaser|fig(?:ure)?1|overview|method', u, re.I):
                return full
            if not best:
                best = full
        if best:
            return best
    return ''


def try_download(url, dest):
    code, ok = curl(url, out=dest)
    if not ok:
        return False
    try:
        parts = code.split()
        status, size = int(parts[0]), int(parts[1])
    except Exception:
        return False
    if status != 200 or size < MIN_BYTES:
        return False
    p = subprocess.run(['file', '--mime-type', '-b', dest], capture_output=True, text=True)
    return 'image/' in (p.stdout or '')


def placeholder(dest, label, accent='#1d4ed8'):
    """无图时生成主题色占位图（纯 SVG，Chromium 可直接渲染）。"""
    label = (label or 'Digest')[:18]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="#0f172a"/>'
           '</linearGradient></defs>'
           '<rect width="800" height="420" fill="url(#g)"/>'
           '<text x="400" y="215" font-family="Noto Sans CJK SC,sans-serif" font-size="46" '
           'font-weight="700" fill="#ffffff" text-anchor="middle" opacity="0.92">{t}</text>'
           '<text x="400" y="262" font-family="Noto Sans CJK SC,sans-serif" font-size="20" '
           'fill="#ffffff" text-anchor="middle" opacity="0.55">Hermes Digest</text>'
           '</svg>').format(a=accent, t=label.replace('&', '&amp;').replace('<', '&lt;'))
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(svg)
    return dest


def fetch_all(items, outdir, accent='#1d4ed8'):
    os.makedirs(outdir, exist_ok=True)
    result = {}
    for it in items:
        key = str(it.get('key') or '')
        link = (it.get('link') or '').strip()
        label = it.get('org') or it.get('title') or 'Digest'
        dest = os.path.join(outdir, 'hero_{}.img'.format(hashlib.md5((key + link).encode()).hexdigest()[:10]))
        # 缓存命中：上次已抓到真图 → 直接用，避免重复抓网
        if os.path.exists(dest) and os.path.getsize(dest) > 15000:
            mm = subprocess.run(['file', '--mime-type', '-b', dest], capture_output=True, text=True).stdout or ''
            if 'image/' in mm:
                result[key] = dest
                continue
        got = False
        try:
            if link.startswith('http'):
                cands = []
                if 'arxiv.org/abs/' in link:
                    a = arxiv_html_image(link)
                    if a:
                        cands.append(a)
                html = page_html(link)
                if html:
                    mi = meta_image(html)
                    if mi:
                        cands.append(urllib.parse.urljoin(link, mi))
                    cands += content_images(html, link)
                for u in cands[:4]:
                    if 'arxiv-logo' in u or SKIP_HINT.search(u):
                        continue
                    if try_download(u, dest):
                        got = True
                        break
        except Exception as ex:      # 单条失败不影响整批
            print('  hero item {} failed: {}'.format(key, ex))
        if not got:
            placeholder(dest + '.svg', label, accent)
            dest = dest + '.svg'
        result[key] = dest
    return result


if __name__ == '__main__':
    items = json.load(open(sys.argv[1], encoding='utf-8'))
    out = fetch_all(items, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '#1d4ed8')
    print(json.dumps(out, ensure_ascii=False))
