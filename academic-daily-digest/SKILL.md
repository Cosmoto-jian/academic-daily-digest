---
name: academic-daily-digest
description: Daily protein/biophysics paper digest, scored and delivered as PDF.
version: 1.1.0
author: Jian Wang (wangjian), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [research, papers, arxiv, biorxiv, rss, digest, cron]
    related_skills: [daily-hot-briefing]
---

# Academic Daily Digest（学术文献日报）

面向生物物理/蛋白质力学/结构生物学方向的学术文献追踪日报。三步流水线：**采集（RSS/PubMed/arXiv）→ 过滤打分去重 → 成文转 PDF**。设计为 cron 定时任务（如每天 17:00），最终以 PDF 附件投递到微信等消息平台。与 AI 新闻日报分开，不混新闻。

## When to Use

- 用户要「文献日报 / paper digest / 每天推文献」并配置 cron
- cron prompt 中指名本 skill
- Don't use for: 科技新闻（用 daily-hot-briefing）、单篇论文问答

## Prerequisites

- Python 3.10+（仅标准库）
- 二选一渲染器：
  - Chromium（推荐，手机卡片版 PDF）：playwright 安装的 headless shell 或系统 chrome。转换器自动探测 `~/.cache/ms-playwright/`，也可用 `CHROME=/path/to/chrome` 指定
  - XeLaTeX（备用，A4 学术版）：`texlive-xetex` + `fonts-noto-cjk`
- 无需任何 API key；网络抓取全部走公开 RSS / PubMed eutils / arXiv API

## How to Run

cron prompt 要点：按本 skill 全流程执行；最终回复第一行输出 `MEDIA:<PDF 绝对路径>`（裸路径、独占一行，网关会作为文件附件投递），后附 3 条必读标题速览。

## Procedure

### 第一步：采集

用 execute_code/terminal + curl（带 UA 头）抓取，脚本先 write_file 落盘再执行（部分环境禁 heredoc）。单源两次失败即放弃，文末注明。

**直接抓 RSS（实测 200 可用）：**
- 1-Core 期刊：BiophysJ `cell.com/biophysj/current.rss`、JMPS `rss.sciencedirect.com/publication/science/00225096`、EML `.../23524316`、NSMB `nature.com/nsmb.rss`、Structure `cell.com/structure/current.rss`、PLOS CompBiol `journals.plos.org/ploscompbiol/feed/atom`
- 2-Methods：`nature.com/{natmachintell|natcomputsci|nmeth}.rss`、`cell.com/cell-systems/current.rss`
- 3-Broad（须过关键词过滤）：`nature.com/{nature|ncomms}.rss`、Science/SciAdv/PNAS etoc、`feeds.aps.org/rss/recent/{prl|prx|pre}.xml`、`elifesciences.org/rss/recent.xml`、JMB `rss.sciencedirect.com/publication/science/00222836`
- arXiv 分类流：`rss.arxiv.org/atom/{q-bio.BM|q-bio.QM|physics.bio-ph|cond-mat.soft|physics.comp-ph|cond-mat.stat-mech}`
- bioRxiv：`connect.biorxiv.org/biorxiv_xml.php?subject={biophysics|bioinformatics}`

**必须走替代路径：**
- JCTC/JCIM（ACS 403 硬拦截）、NSR（OUP RSS 404）→ PubMed eutils：`eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=<期刊[jour]+AND+关键词[tiab]>&retmax=20&sort=date`，详情用 efetch
- arXiv API 检索（export.arxiv.org/api/query）本机 IP 可能限流：可用时优先（间隔 ≥3s）；被限则降级用分类流 + 客户端关键词过滤

单源 ≤15 条，总量 ≤40 条。

### 第二步：过滤、打分、去重

- 3-Broad 综合刊与 arXiv 全量流必须过标题关键词过滤（不分大小写），词表见 `references/filters.md`；宁宽勿严
- 每条 0–100 分：novelty 与 credibility 优先，resonance 弱化；综述/方法文/反直觉结果酌情加分；纯增量/案例报告压分
- 同一工作多源重复只留信息量最大的一条
- **跨天去重（硬规则）**：成文前读存档目录下最近 3 份学术日报的标题与 🔗 链接，同一论文（同 DOI/arXiv ID 或同标题）且无实质新增内容 → 不再收录。宁少勿重，禁止旧闻凑数

### 第三步：存盘、转 PDF、投递

1. 成文存 `<存档目录>/YYYY-MM-DD-academic.md`（默认 `~/briefings/`）。**每条必须带 🔗 链接行**（arXiv → `https://arxiv.org/abs/{id}`；bioRxiv → doi 链接；期刊 RSS → `<link>` 字段；PubMed → `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`）
2. 转手机卡片版 PDF（推荐）：
   `python3 <skill目录>/scripts/digest_to_mobile_pdf.py <in.md> <out.pdf> --style academic`
   确认输出 BUILD_OK 且 PDF 存在。备选 A4 LaTeX 版：`scripts/academic_md_to_tex.py`（需 XeLaTeX + Noto CJK）
3. 最终回复第一行 `MEDIA:<PDF 绝对路径>` 独占一行（不加代码块），后附 3 条必读标题速览

## Quick Reference

```
scripts/digest_to_mobile_pdf.py <in.md> <out.pdf> [--style academic|news] [--no-hero]
scripts/academic_md_to_tex.py    <in.md> <out.pdf>
```

## 存档条目格式

两种格式转换器均兼容：
- 新格式：`### N. 标题 [NN/100]` + 摘要正文行 + `🔗 url` + 来源行
- 旧格式：`- **期刊** | 标题 — 摘要` + `🔗 url`

图文规则：转换器按 🔗 链接自动抓主图（arXiv teaser 图、期刊 og:image），抓不到的条目不放图。**链接行是抓图依据，每条务必带 🔗**（详见 `references/report-format.md`）。

## Pitfalls

- bioRxiv XML 是 RDF 格式：条目用 `<item rdf:about="...">` 正则解析（普通 `<item>` 匹配不到），title/description 带 CDATA 要剥壳，链接去 `?rss=1` 后缀
- arXiv 分类流可能返回空 feed → 降级用 export.arxiv.org/api/query 按 cat 组合检索
- cron 环境常禁 heredoc/python -c：抓取脚本先 write_file 落盘再 `python3 路径` 执行
- 微信 iLink 报 `session not ready: ret=-2` 是会话过期：让用户先给 bot 发消息激活后重推即可，无需改配置
- MEDIA 行前后不要加代码块或多余文字，第一行必须是裸路径

## Verification

- PDF 文件存在且 >5KB，转换器输出 BUILD_OK
- 每条目有 🔗 链接且跨天无重复（与最近 3 份存档比对）
- 抓取失败的源在文末注明；**不伪造文献条目**。PDF 编译失败时改为输出微信纯文本版全文并注明「PDF 生成失败」
