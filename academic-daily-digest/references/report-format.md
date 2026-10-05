# 学术日报格式（微信 PDF：手机图文卡片版式）

最终交付改为 **Chromium 打印的手机竖版 PDF**（100mm 宽，卡片式布局，彩色 emoji，支持链接点击），不再是 A4 LaTeX 版。转换器：`python3 ~/briefings/tools/digest_to_mobile_pdf.py <input.md> <output.pdf> --style academic`（AI 日报用 --style news，同一脚本两种主题）。

存档 Markdown 结构不变：## 节标题；条目（### 标题 [NN/100] 或 - **期刊** | 标题 — 摘要）+ 🔗 链接行 + 摘要行。转换器自动解析，无需为 PDF 改写格式。

**图文规则**：转换器按每条的 🔗 链接自动抓取主图（arXiv → HTML 版 teaser 图；Nature/期刊页 → og:image 首图；抓不到 → 该条不放图，无占位）。有真图的条目图完整显示不裁切。链接行是抓图依据，**每条务必带 🔗**。
