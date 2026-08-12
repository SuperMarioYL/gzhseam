<div align="right"><sub><b>简体中文</b>&nbsp;&nbsp;⇄&nbsp;&nbsp;<a href="./README.en.md">English</a></sub></div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
  <img src="./assets/hero-light.svg" width="880" alt="GzhSeam — coding-agent HTML → 公众号 native editable HTML">
</picture>

<p align="center"><sub>GzhSeam 是 coding agent 与公众号原生编辑器之间的 seam：把 Claude Code（或任意 Skill）生成的 HTML 图文洗成公众号标签白名单合规、图片走公众号 CDN、字体合规、可在公众号编辑器就地改一个字的可发布 HTML。</sub></p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT"></a>
  <img src="https://img.shields.io/github/v/release/SuperMarioYL/gzhseam" alt="latest release">
  <img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/gzhseam/ci.yml?label=ci" alt="ci">
  <img src="https://img.shields.io/badge/python-3.12+-blue" alt="python 3.12+">
  <img src="https://img.shields.io/badge/Agent-Ready-8985FF" alt="Agent-Ready">
  <img src="https://img.shields.io/badge/Skill-Companion-2DC79A" alt="Skill-Companion">
</p>

**把 coding-agent 出的 HTML 洗成公众号编辑器能接住的可发布 HTML —— 一条命令，12 张图的 deck 30s 内出活，不用回 agent 改一个字。**

<h2><img src="https://api.iconify.design/tabler:topology-star-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 架构</h2>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
  <img src="./assets/atlas-light.svg" width="880" alt="架构：deck.html → gzhseam wash (whitelist · fonts · cdn) → out.html (公众号-pasteable)">
</picture>

GzhSeam 的核心原语是 **GzhWash pipeline** —— 一个确定性、有序的 HTML 树变换，产出的 HTML 资产在「coding-agent 作者侧」和「公众号编辑器侧」两端都仍可续改。三段洗按顺序跑：

1. `whitelist.filter` — 用 lxml 走树，drop 平台不兼容的标签（`<script>` / `<canvas>` / `<iframe>` / `<video>` / `<style>` / `<link>` / `<meta>` / …）、unwrap 非白名单但内容需要保留的标签、剥离所有 `on*` 事件属性与非白名单属性。
2. `fonts.normalize` — inline style 里的 `font-family` 重映射到公众号允许的字体集；外链 web-font（`"Fira Code"`、`"Operator Mono"`、`"Inter Tight"` …）按 sans / serif / mono 桶降级到默认链，保留作者意图。
3. `cdn.replace` *(m2 stub)* — 下载外部 `<img src>`，POST 到公众号素材上传 API，把 src 改指公众号 CDN URL。

**Why now.** coding agent 已经从「新奇」跨到「默认作者工具」——Bento 的作者在 [HN 188 分帖](https://news.ycombinator.com/item?id=40569579) 里直接说他的用户「to make even small edits we need to edit the code either manually or via the harness」，而 [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) 在 ~3 个月内堆到 22k★ 证明这个 Skill 工作流已经在 CN 创作者圈规模化。Agent 把生成层做便宜了，瓶颈就推到 publish-conform 这层——[HKUDS](https://github.com/HKUDS) 的 agent-tooling 研究线已经在追这一层；GzhSeam 接的就是这层缝。公众号在这段时间还在收紧外链图 strip + 收紧标签白名单，所以「能贴进去」的门槛在变高而不是变低。

<h2><img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 安装</h2>

```bash
git clone https://github.com/SuperMarioYL/gzhseam.git && cd gzhseam
pip install -e .
gzhseam wash tests/fixtures/sample_deck.html -o gzh-ready.html
```

一行装好（uvx 自带 Python，发布到 PyPI 后）：

```bash
uvx gzhseam wash deck.html -o gzh-ready.html
```

<details><summary>sample 输出（<code>--verbose</code>）</summary>

```
→ 解析 HTML (1 个 deck, 1 张图)
→ 过滤标签白名单 (移除 <script>, <canvas>, on* 事件)
→ 字体规整 (font-family → 公众号允许集)
✓ gzh-ready.html 已生成（纯本地洗，可直接贴入公众号编辑器就地改一个字）
  ! dropped <meta> (platform-incompatible)
  ! dropped <script> (platform-incompatible)
  ! dropped <canvas> (platform-incompatible)
  ! unwrapped <agent-deck> (not in whitelist)
  ! <section>: stripped attrs ['onclick']
  · font-family: "'Fira Code', monospace" -> 'monospace'
```

</details>

<h2><img src="https://api.iconify.design/tabler:terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 用法</h2>

```bash
# 1. m1 主路径：本地洗一份 coding-agent 出的 HTML deck
gzhseam wash my-deck.html -o gzh-ready.html

# 2. 同上，附带每条 violation / font-rewrite 的诊断输出
gzhseam wash my-deck.html -o gzh-ready.html --verbose

# 3. m2 预览：加 --cdn 会触发公众号 CDN 上传阶段（m1 stub，会报 NotImplementedError 指向路线图）
gzhseam wash my-deck.html -o gzh-ready.html --cdn

# 4. 版本号 / 帮助
gzhseam --version
gzhseam wash --help
```

更多示例见 [`examples/wash_a_deck.md`](./examples/wash_a_deck.md)。CLI 用法是单条 `gzhseam wash` —— 公众号编辑器本身就是就地 WYSIWYG，CLI + 编辑器已经闭环（不做 Web UI，不重复造编辑器）。

<h2><img src="https://api.iconify.design/tabler:photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Demo</h2>

![demo](./assets/demo.gif)

vhs 录制脚本在 [`docs/demo.tape`](./docs/demo.tape) —— 用 `vhs docs/demo.tape` 本地重渲染，或用 GitHub Actions 的 **demo** workflow（`workflow_dispatch` 手动触发）在线重渲。仓库里提交的 `assets/demo.gif` 是事实源，工作流只在需要刷新时跑。

<h2><img src="https://api.iconify.design/tabler:adjustments.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 配置</h2>

m1 不需要任何配置——纯本地变换，无网络。下表是 m1+m2 全集：

| key | type | default | meaning |
|---|---|---|---|
| `~/.gzhseam/credentials.toml` | file | absent | 公众号 AppID + AppSecret（m2 `gzhseam init` 交互式写入；m1 不需要） |
| `~/.gzhseam/access_token.json` | file | absent | 缓存的公众号 access_token（m2，TTL ~120min，提前 30min 刷新） |
| `--cdn` / `--no-cdn` | CLI flag | `--no-cdn` | 是否跑 m2 图片 CDN 上传阶段 |

<h2><img src="https://api.iconify.design/tabler:map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 路线图</h2>

- [x] **m1 — 标签白名单 + 字体规整**（纯本地，无网络；`pytest tests/` 全绿）
- [ ] **m2 — 公众号 API 鉴权 + 图片 CDN 上传**：`gzhseam auth login` 换 access_token（缓存 ~90 min），`wash --cdn` 把所有外部 `<img src>` 替换为公众号 CDN URL。**前置 kill-gate**：开始前先实测当前公众号平台规则——若公众号已放宽标签白名单 / 不再 strip 外链图，护城河塌，halt。
- [ ] **m3 — 端到端 CLI**：`gzhseam wash deck.html -o out.html` 一键从 coding-agent HTML 到公众号可编辑 HTML + README 双语 + demo gif
- [ ] **v0.2 — hosted 公众号 pre-publish queue SaaS**：多账号 + 草稿审阅 + 定时入队 + 团队成员 seat（面向工作室 / MCN 矩阵运营团队）
- [ ] 季度复查公众号平台规则漂移（白名单放宽 / 外链图放开即触发 m2 kill-gate 复评）

<h2><img src="https://api.iconify.design/tabler:chart-bar.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> vs guizang-ppt-skill</h2>

GzhSeam 与 [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill)（22k★，公众号 HTML-deck Skill）是天然互补，不是竞争——guizang 出 deck，GzhSeam 出公众号。各做各强项的那一段：

| 维度 | GzhSeam | [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) |
|---|:---:|:---:|
| 生成 HTML deck（幻灯片 / 杂志布局 / social cover） | ✗ | ✓ 强项 |
| 公众号标签白名单合规 | ✓ deterministic 过滤 | ✗ deck 用 WebGL/canvas 等，粘进公众号被 strip |
| 公众号 CDN 图片托管 | ✓ (m2) 上传外链图到公众号 CDN | ✗ 图床走外部图床（公众号会 strip） |
| 字体规整到公众号允许集 | ✓ | ✗ 自由选 web-font，粘进公众号被重置 |
| 就地改一个字（公众号编辑器 WYSIWYG） | ✓ 输出 HTML 两端续改 | ✗ 改字回 Claude Code + Skill 重跑 |

guizang 在「生成 deck」这一维度上明显更强——GzhSeam 不生成 deck，只洗 HTML。两者组合的完整工作流是 `guizang-ppt-skill → 出 deck → GzhSeam wash → 公众号编辑器就地续改 → 发布`。

<h2><img src="https://api.iconify.design/tabler:currency-dollar.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 付费</h2>

v0.1 是个人免费 OSS——这条 seam 对所有创作者免费。商业延伸 = v0.2 hosted **公众号 pre-publish queue** SaaS，面向中小内容工作室 / MCN 公众号矩阵运营团队（3–10 个公众号账号，每周 5–20 篇图文 deck 走 coding agent 出），他们已经过了单 CLI 的适用边界：

- **多账号 binding** —— 一个 workspace 绑 ≤5 个公众号，共享 access_token 频控缓存（公众号 45009 限频在 hosted 层共享比 CLI per-instance 缓存更省）
- **草稿审阅 queue** —— 团队成员 seat 协作审稿、批注、回滚
- **定时入队** —— 草稿进 queue，到点自动 wash 并贴入编辑器草稿箱
- **座席管理** —— per-workspace 月费 ¥199（≤5 binding、3 seats、100 篇/月 wash 配额），额外座席 ¥99/seat/月，超配额 ¥2/篇

**首次付费触发条件**：v0.1 上线后 30 天内收到 ≥3 个「多账号 / 团队」入站需求 OR 1 个工作室 owner 主动付 ¥199 → 立即启动 v0.2 hosted 开发。若 60 天内零「团队/多账号」入站信号 → 商业延伸缓做，重新评估。

个人用户永远免费；为团队需求付费，不为个人工具付费。

<h2><img src="https://api.iconify.design/tabler:history.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> 更新日志</h2>

- **v0.4.0** — wash 边界硬化：仅含 head 级标签（`<script>`/`<style>`/`<meta>`/`<title>`/`<link>`，均属 DROP_TAGS）的 deck 不再泄漏 `<html><head>` 文档外壳——`_serialize_fragment` 与 `fonts.normalize_fonts` 在 lxml 未生成 `<body>` 时返回空片段，而非回退到整文档；`gzhseam wash` 对空 / 仅空白（或洗后无残留）的输入改为干净失败：红 `✗` + `sys.exit(2)`、不写 0 字节文件，对齐 v0.3.0 的 clean-failure 模式。
- **v0.3.0** — wash 边界用例的 clean-failure 修复：非 UTF-8 输入、缺失输出目录、`init`/`auth login` 存根不再抛裸 traceback，统一红 `✗` + `sys.exit(2)`。

<h2><img src="https://api.iconify.design/tabler:license.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> License</h2>

MIT —— 见 [LICENSE](./LICENSE)。问题、bug、PR 走 [GitHub Issues](https://github.com/SuperMarioYL/gzhseam/issues)。

**推送后设置 repo topic（建议）：**

```bash
gh repo edit --add-topic gongzhonghao --add-topic html \
  --add-topic coding-agent --add-topic publish-format --add-topic wechat \
  --add-topic agent --add-topic skill
```

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>

<h2><img src="https://api.iconify.design/tabler:share-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Share this</h2>

```
GzhSeam — Agent 与公众号编辑器之间的那层缝。一条命令把 coding-agent 出的 HTML deck 洗成公众号白名单合规、可在编辑器就地改一个字的可发布 HTML。https://github.com/SuperMarioYL/gzhseam
```
