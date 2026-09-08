[English](README.en.md) | **简体中文**

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/hero-dark.svg">
  <img src="assets/presentation/hero-light.svg" width="1000" alt="按明确的标签、属性和字体规则转换 HTML，输出可继续编辑的文章片段与诊断信息。">
</picture>

**按明确的标签、属性和字体规则转换 HTML，输出可继续编辑的文章片段与诊断信息。**

`v0.5.0` · `Python 3.12+` · [MIT](LICENSE)

[Website](https://gzhseam.lei6393.com) · [Demo record](docs/demo-results.json)

## 为什么使用

生成的 HTML 往往含脚本、嵌入内容和自定义字体，复制到文章编辑器后可能变化。GzhSeam 先按仓库规则做本地变换，报告删除和字体映射，让作者查看产物再交给目标平台。

## 架构

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/architecture-dark.svg">
  <img src="assets/presentation/architecture-light.svg" width="1000" alt="washer.py 依次调用 whitelist.filter_html 与 fonts.normalize_fonts。前者删除指定标签、展开非白名单容器并剥离属性，后者整理 inline font-family。GzhCtx 的 per-call 覆盖在 v0.5.0 已透传。CDN 阶段仍为 stub。">
</picture>

washer.py 依次调用 whitelist.filter_html 与 fonts.normalize_fonts。前者删除指定标签、展开非白名单容器并剥离属性，后者整理 inline font-family。GzhCtx 的 per-call 覆盖在 v0.5.0 已透传。CDN 阶段仍为 stub。

规则见 [whitelist.py](gzhseam/whitelist.py) 和 [fonts.py](gzhseam/fonts.py)，编排见 [washer.py](gzhseam/washer.py)。这些是项目定义的规则，不是本次实时核验的公众号平台规范。

## 安装

需要 Python 3.12+。本地 wash 不需要公众号凭据，也不会下载示例中的远程图片。

```bash
git clone https://github.com/SuperMarioYL/gzhseam.git
cd gzhseam
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 快速开始

真实 CLI 清洗完整 HTML fixture，随后读回产物并检查二次处理与自定义白名单。没有上传图片、登录公众号或验证编辑器粘贴效果。

```bash
python -m gzhseam.cli wash examples/presentation-input.html -o examples/presentation-output.html --verbose
python examples/presentation_inspect.py
```

输入为 [presentation-input.html](examples/presentation-input.html)，结果为 [presentation-output.html](examples/presentation-output.html)；第二步的所有检查在 [脚本](examples/presentation_inspect.py) 中。

## 使用

wash FILE -o OUTPUT 执行本地转换，--verbose 输出每条诊断。空、非 UTF-8 或洗后无内容的输入会失败。--cdn、init 和 auth login 当前仍未实现；不要把这些命令当作已接通的图片或鉴权服务。

## 实际 Demo

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/process-dark.svg">
  <img src="assets/presentation/process-light.svg" width="1000" alt="真实 CLI 清洗完整 HTML fixture，随后读回产物并检查二次处理与自定义白名单。没有上传图片、登录公众号或验证编辑器粘贴效果。">
</picture>

### 执行本地 wash

查看标签、属性和字体的实际诊断。

```text
$ python -m gzhseam.cli wash examples/presentation-input.html -o examples/presentation-output.html --verbose
→ 解析 HTML (1 个 deck, 1 张图)
→ 过滤标签白名单 (移除 <script>, <canvas>, on* 事件)
→ 字体规整 (font-family → 公众号允许集)
✓ examples/presentation-output.html 已生成（纯本地洗，可直接贴入公众号编辑器就地改一个字）
  ! unwrapped <article> (not in whitelist)
  ! dropped <script> (platform-incompatible)
  ! unwrapped <custom-note> (not in whitelist)
  · font-family: "'Fira Code', monospace" -> 'monospace'
```

### 读回与覆盖

检查二次处理相等，并演示只允许 p 标签。

```text
$ python examples/presentation_inspect.py
{
  "html": "<h1 style=\"font-family: monospace;\">Local article</h1><p>Keep this text.</p><img alt=\"illustrative remote image\" src=\"https://example.invalid/picture.png\"/>",
  "second_pass_same": true,
  "restricted_html": "<p>Paragraph</p>Link text"
}
```

## 能力与接入

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/integrations-dark.svg">
  <img src="assets/presentation/integrations-light.svg" width="1000" alt="工具整理 HTML，不生成文章、不替平台审核，也不自动发布。CLI 的成功信息表示本地转换写入完成，不能直接当作公众号兼容性验收。">
</picture>

工具整理 HTML，不生成文章、不替平台审核，也不自动发布。CLI 的成功信息表示本地转换写入完成，不能直接当作公众号兼容性验收。



## 配置

默认不需要配置文件。Python 调用可通过 GzhCtx.whitelisted_tags、allowed_attrs、allowed_fonts 覆盖规则；upload_cdn 默认关闭。模型输入、媒体链接和 inline style 的所有语义并不会被理解，输出仍需人工检查。

## 路线图与范围

当前是本地标签、属性与字体变换工具。公众号鉴权、CDN 上传、团队审稿队列和托管收费方案都仍是后续方向，没有已上线服务或已确认定价。

- 规则来自仓库，未实时验证目标平台当前粘贴行为。
- CDN、认证与自动发布不在已实现路径中。
- HTML 规则转换不是通用安全证明或完整浏览器沙箱。

[Terminal recording](assets/demo.gif) · [Recording script](docs/demo.tape)

## 许可证

[MIT](LICENSE)
