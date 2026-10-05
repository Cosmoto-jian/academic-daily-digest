# academic-daily-digest

Hermes Agent skill：面向生物物理/蛋白质力学/结构生物学方向的**学术文献日报**，自动采集 → 打分 → 生成手机卡片版 PDF，推送到微信等消息平台。

每天一封 ~3 页的图文卡片 PDF，含 arXiv/bioRxiv/Nature/Cell/Science/PNAS 等 20+ 信源，自动抓取论文主图、可点击跳转原文。

![示例](https://img.shields.io/badge/platform-Hermes_Agent-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## 一键安装（Hermes Agent）

在任意 Hermes 会话里说：

```
/skills install <你的GitHub用户名>/skills/main/academic-daily-digest
```

或命令行：

```bash
hermes skills install <你的GitHub用户名>/skills/main/academic-daily-digest
```

Hermes 会自动下载 `SKILL.md` + 全部引用的 `references/` 和 `scripts/` 文件，完成安全扫描后装入 `~/.hermes/skills/`。

手动安装（其他 agent 也适用）：把 `academic-daily-digest/` 整个目录复制到你的 skills 目录即可。

## 使用

安装后对 Hermes 说：

- 「帮我配置每天下午 5 点的学术文献日报」（agent 会创建 cron 任务）
- 或 `/academic-daily-digest 生成今天的文献日报`

## 依赖

- Python 3.10+（仅标准库）
- PDF 渲染二选一：
  - **Chromium**（推荐）— playwright 的 headless shell 或系统 chrome，自动探测，或 `CHROME=` 指定
  - **XeLaTeX**（备用 A4 版）— `texlive-xetex fonts-noto-cjk`
- 无需 API key（全部公开 RSS / PubMed eutils / arXiv API）

## 定制你的领域

关键词过滤词表在 `academic-daily-digest/references/filters.md`，信源清单在 `SKILL.md` 的「第一步：采集」。改成你自己的研究方向只需要改这两处。

## 结构

```
academic-daily-digest/
├── SKILL.md                      # 主流程（采集→打分→PDF→投递）
├── references/
│   ├── filters.md                # 领域关键词过滤词表
│   └── report-format.md          # 成文/PDF 图文格式规则
└── scripts/
    ├── digest_to_mobile_pdf.py   # Markdown → 手机卡片版 PDF（Chromium）
    ├── academic_md_to_tex.py     # Markdown → A4 LaTeX PDF（XeLaTeX）
    └── fetch_hero_images.py      # 自动抓取论文主图（arXiv teaser/og:image）
```

## License

MIT © Jian Wang
