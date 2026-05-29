# 期末复习.skill

`期末复习.skill` 是一个面向 Codex / Claude Code / OpenClaw 等 Agent 工具的课程资料整理技能包。它可以把一个文件夹里的英文课件 `.pptx` 和中文教材 `.pdf` 自动整理成一份适合期末考试复习的中文 Obsidian Markdown 笔记。

> 仓库展示名采用 `期末复习.skill`；由于 GitHub 仓库 slug 会规范化中文字符，远端仓库地址使用 `qimo-fuxi.skill`。为了兼容 Codex / OpenClaw 的技能命名规则，技能 ID 仍然保留为 `course-exam-note`，调用时使用 `$course-exam-note`。

## 适用场景

这个 skill 适合以下课程复习任务：

- PPTX 课件主要是英文；
- 原教材或参考资料是中文 PDF；
- 最终希望得到一份从零开始也能学懂的期末复习笔记；
- PPTX 内所有可抽取知识点都必须覆盖；
- 专业术语需要翻译准确、表达严谨；
- 重要表格、流程图、结构图等图片资源需要插入到对应章节知识点附近；
- 不希望批量导出每页 PPT 截图，以免速度慢、文件大、消耗 token。

## 核心能力

- 自动扫描课程文件夹内的 `.pptx` 和 `.pdf`。
- 抽取 PPTX 中的标题、正文、项目符号、表格、备注页、XML 文本节点、图片 alt text 和原始嵌入图片。
- 抽取中文 PDF 教材文本，以及较大的语义图片候选。
- 不批量渲染每页幻灯片截图。
- 自动识别 SmartArt、组合形状、连接线密集的复杂视觉页，并放入待人工复核清单。
- 生成结构化素材包，供 Agent 继续生成最终笔记。
- 约束最终笔记以“按章节整理的完整知识点”为核心。
- 要求专业术语在正文首次出现时标注英文，例如：`关系代数（Relational Algebra）`。

## 仓库结构

```text
期末复习.skill/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   └── note_policy.md
└── scripts/
    └── build_source_pack.py
```

## 环境要求

- Python 3。
- 首次运行时需要网络访问，用于安装缺失依赖。
- 推荐配合 Obsidian 使用；如果有 Obsidian MCP 或 Local REST API 工作流，Agent 可以直接把最终笔记写入 vault。

脚本会自动创建专用虚拟环境：

```text
~/.codex/cache/course-exam-note/venv
```

首次运行时会在这个虚拟环境中安装：

```text
python-pptx
PyMuPDF
Pillow
lxml
```

这样不会污染系统 Python 环境。

## 在 Codex 中使用

安装到全局 Codex skills 目录：

```bash
git clone https://github.com/Qyjay/qimo-fuxi.skill.git ~/.codex/skills/course-exam-note
```

然后在课程资料文件夹中对 Codex 说：

```text
Use $course-exam-note to turn this folder's PPTX and PDF course materials into a complete Obsidian exam-study note.
```

也可以直接运行素材包构建脚本：

```bash
python3 ~/.codex/skills/course-exam-note/scripts/build_source_pack.py /path/to/course-folder
```

脚本会生成：

```text
/path/to/course-folder/.course-exam-note/<run-id>/
├── source_pack.json
├── raw_slides.md
├── raw_textbook.md
├── coverage.json
├── coverage.md
├── visual_review.md
└── generation_prompt.md
```

图片资源会生成到：

```text
/path/to/course-folder/assets/course-exam-note/<run-id>/
```

如果课程文件夹位于 Obsidian vault 内，这些图片路径可以直接用于 Obsidian wiki embed。

## 最终笔记要求

最终笔记应当围绕章节知识点组织，而不是按 PPT 文件或页码机械罗列。

推荐结构：

```markdown
# 课程总览

# 期末复习路线

# 按章节整理的完整知识点

# 易错点与记忆提示

# 待人工复核的复杂图示页
```

硬性要求：

- 面向一个完全没上过这门课、准备期末考试的学生来写。
- 重点放在每章的知识点总结上。
- 不生成独立的 `核心术语表`。
- 不在最终笔记中生成 PPT 覆盖索引。
- 英文课件内容翻译为专业、严谨的中文。
- 重要专有名词首次出现时保留英文。
- 使用中文 PDF 教材校正术语，并补充 PPT 中不清楚或不准确的部分。
- 补充说明要短，服务于理解和考试记忆，不写成长篇教材复述。
- 重要图片资源必须插入对应章节知识点附近，不集中堆到最后。

Obsidian 图片引用示例：

```markdown
![[assets/course-exam-note/<run-id>/ppt-media/example.png]]
```

如果某页 PPT 包含无法通过结构化抽取完整还原的复杂图示，在对应知识点附近加入简短提示：

```markdown
> [!warning] 该知识点在课件中包含复杂图示，已提取文字内容，建议复核原始 PPT 的视觉关系。
```

## 适配 Claude Code

Claude Code 可以直接使用这个仓库，因为它本质上是 `SKILL.md`、规则文档和 Python 脚本组成的普通文件夹。

### 方法一：直接引用 skill 文件

先克隆仓库：

```bash
git clone https://github.com/Qyjay/qimo-fuxi.skill.git /path/to/期末复习.skill
```

然后在 Claude Code 中输入：

```text
请使用 /path/to/期末复习.skill/SKILL.md 中定义的工作流。
先运行 scripts/build_source_pack.py 分析当前课程资料文件夹，
再读取 references/note_policy.md，
最后生成一份中文 Obsidian 期末复习 Markdown 笔记。
```

### 方法二：做成 Claude Code 自定义 Slash Command

Claude Code 支持把 Markdown 文件放在 `.claude/commands/` 下作为自定义 slash command。

在你的课程项目中创建命令：

```bash
mkdir -p .claude/commands
cat > .claude/commands/course-exam-note.md <<'EOF'
使用 course-exam-note 工作流整理当前课程资料。

1. 读取 /path/to/期末复习.skill/SKILL.md。
2. 对当前课程资料文件夹运行 /path/to/期末复习.skill/scripts/build_source_pack.py。
3. 读取生成的 generation_prompt.md、raw_slides.md、raw_textbook.md 和 visual_review.md。
4. 遵循 /path/to/期末复习.skill/references/note_policy.md。
5. 输出一份中文 Obsidian 期末复习 Markdown 总笔记。

不要生成独立核心术语表。
不要在最终笔记中放 PPT 覆盖索引。
重点放在每章的知识点总结上。
EOF
```

之后在 Claude Code 中调用：

```text
/course-exam-note
```

## 适配 OpenClaw

OpenClaw 的 skill 也是 Markdown 中心的技能文件夹，可以把这个仓库放到常见 skills 目录中，例如：

```text
<workspace>/skills/
<workspace>/.agents/skills/
~/.agents/skills/
~/.openclaw/skills/
```

全局安装示例：

```bash
git clone https://github.com/Qyjay/qimo-fuxi.skill.git ~/.openclaw/skills/course-exam-note
```

然后对 OpenClaw 说：

```text
使用 course-exam-note skill 扫描当前文件夹内的 PPTX 和 PDF 课程资料，
生成一份按章节知识点组织的中文 Obsidian 期末复习笔记。
```

如果你的 OpenClaw 配置需要显式启用 skill，请把 `course-exam-note` 加入对应 agent 的 enabled skills 或 allowlist。

## 手动运行脚本

```bash
python3 scripts/build_source_pack.py /path/to/course-folder
```

常用参数：

```bash
python3 scripts/build_source_pack.py /path/to/course-folder --run-id stable-run
python3 scripts/build_source_pack.py /path/to/course-folder --vault-dir /path/to/ObsidianVault
python3 scripts/build_source_pack.py /path/to/course-folder --no-install
```

参数说明：

- `--run-id`：指定稳定输出目录名，便于复跑和对比。
- `--vault-dir`：指定 Obsidian vault 根目录。
- `--no-install`：禁止自动安装依赖；只有在当前 Python 环境已装好依赖时才建议使用。

## 生成物说明

`source_pack.json`：结构化素材包，包含 PPTX/PDF 抽取结果。

`raw_slides.md`：可读版 PPTX 原始素材，包括文字、表格、备注、图片候选。

`raw_textbook.md`：PDF 教材文本和图片候选。

`coverage.json` / `coverage.md`：内部覆盖审计文件，只用于确认 PPT 可抽取内容已处理，不应放入最终笔记。

`visual_review.md`：复杂视觉页清单，用于提醒人工复核。

`generation_prompt.md`：生成最终 Obsidian 笔记时可以直接使用的提示词。

## 安全说明

- 脚本不会上传课程资料。
- 脚本不会批量导出每页 PPT 截图。
- 脚本会在课程目录下写入 `.course-exam-note/<run-id>/` 中间产物。
- 脚本会在 `assets/course-exam-note/<run-id>/` 写入提取出的图片资源。
- 首次运行可能会在 `~/.codex/cache/course-exam-note/venv` 安装 Python 依赖。

## 许可证

当前尚未声明许可证。如果你希望这个仓库作为开源项目供他人复用，建议后续补充 `LICENSE` 文件。
