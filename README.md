# course-exam-note

`course-exam-note` is a Codex skill for turning a folder of course `.pptx` slides and Chinese `.pdf` textbook materials into one detailed Chinese Obsidian Markdown note for final-exam study.

It is designed for courses where:

- the slides are mainly in English;
- the textbook or reference PDF is in Chinese;
- the final output should be a zero-to-exam study note;
- all extractable PPT knowledge points must be covered;
- important diagrams and tables should appear inside the relevant chapter sections, not in a separate image dump.

## What It Does

- Scans a course folder for `.pptx` and `.pdf` files.
- Extracts PPTX slide titles, bullets, tables, speaker notes, XML text nodes, image alt text, and original embedded images.
- Extracts Chinese PDF textbook text and large semantic image candidates.
- Does not batch-render every slide screenshot, keeping the workflow faster and lower-token.
- Flags complex visual slides such as SmartArt, grouped shapes, and connector-heavy flow diagrams for manual visual review.
- Produces a structured source pack for an agent to write a final Obsidian note.
- Enforces a chapter-centered final note:
  - no standalone core terminology table;
  - no PPT coverage index in the final note;
  - professional Chinese translation;
  - important English terms marked inline on first mention, for example `关系代数（Relational Algebra）`.

## Repository Layout

```text
course-exam-note/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   └── note_policy.md
└── scripts/
    └── build_source_pack.py
```

## Requirements

- macOS, Linux, or another environment with Python 3.
- Network access on first run if dependencies are missing.
- Optional but recommended: Obsidian with an MCP or Local REST API workflow for writing the final note into a vault.

The script automatically creates a dedicated virtual environment at:

```text
~/.codex/cache/course-exam-note/venv
```

It installs these Python packages there when needed:

```text
python-pptx
PyMuPDF
Pillow
lxml
```

This avoids polluting the system Python environment.

## Quick Start With Codex

Install the skill globally:

```bash
git clone https://github.com/Qyjay/course-exam-note.git ~/.codex/skills/course-exam-note
```

Then ask Codex from a course-material folder:

```text
Use $course-exam-note to turn this folder's PPTX and PDF course materials into a complete Obsidian exam-study note.
```

The skill first builds a source pack:

```bash
python3 ~/.codex/skills/course-exam-note/scripts/build_source_pack.py /path/to/course-folder
```

Generated artifacts:

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

Image assets are written to:

```text
/path/to/course-folder/assets/course-exam-note/<run-id>/
```

If the course folder is inside an Obsidian vault, the asset paths are ready for Obsidian wiki embeds.

## Final Note Rules

The final note should use this shape:

```markdown
# 课程总览

# 期末复习路线

# 按章节整理的完整知识点

# 易错点与记忆提示

# 待人工复核的复杂图示页
```

Important constraints:

- Write for a student who did not attend the course.
- Organize by chapter and knowledge point, not by PPT page.
- Do not create a standalone `核心术语表`.
- Do not include a PPT coverage index in the final note.
- Use the Chinese PDF textbook to correct terminology and clarify vague slides.
- Keep textbook supplements concise and exam-oriented.
- Insert important images near the knowledge point they explain.
- Use Obsidian embeds such as:

```markdown
![[assets/course-exam-note/<run-id>/ppt-media/example.png]]
```

When a complex slide cannot be faithfully reconstructed without rendering it, add a concise warning near the matching knowledge point:

```markdown
> [!warning] 该知识点在课件中包含复杂图示，已提取文字内容，建议复核原始 PPT 的视觉关系。
```

## Using With Claude Code

Claude Code can use this repository in two practical ways.

### Option A: Project Instruction

Clone the repository anywhere, then tell Claude Code:

```text
Use the skill at /path/to/course-exam-note/SKILL.md.
Run scripts/build_source_pack.py on this course folder.
Then follow references/note_policy.md to produce the final Obsidian Markdown note.
```

This works because the skill is plain Markdown plus a deterministic Python script.

### Option B: Custom Slash Command

Claude Code supports custom slash commands defined as Markdown files under `.claude/commands/`.

Create a command file in your project:

```bash
mkdir -p .claude/commands
cat > .claude/commands/course-exam-note.md <<'EOF'
Use the course-exam-note workflow from this repository:

1. Read /path/to/course-exam-note/SKILL.md.
2. Run /path/to/course-exam-note/scripts/build_source_pack.py on the current course folder.
3. Read the generated generation_prompt.md, raw_slides.md, raw_textbook.md, and visual_review.md.
4. Follow /path/to/course-exam-note/references/note_policy.md.
5. Produce one Chinese Obsidian Markdown final-exam study note.

Do not create a standalone core terminology section.
Do not put a PPT coverage index in the final note.
EOF
```

Then invoke:

```text
/course-exam-note
```

Reference: Anthropic documents custom slash commands for Claude Code as Markdown prompt files under `.claude/commands/`.

## Using With OpenClaw

OpenClaw skills are also Markdown-centered and can live in skills roots such as:

```text
<workspace>/skills/
<workspace>/.agents/skills/
~/.agents/skills/
~/.openclaw/skills/
```

Install globally:

```bash
git clone https://github.com/Qyjay/course-exam-note.git ~/.openclaw/skills/course-exam-note
```

Then ask OpenClaw:

```text
Use the course-exam-note skill to scan this folder's PPTX and PDF materials and create a chapter-centered Chinese final-exam Obsidian note.
```

If your OpenClaw setup requires explicit skill allowlists, add `course-exam-note` to the relevant agent's enabled skills. Review the script before enabling it in highly restricted environments because it installs Python dependencies into a local venv on first run.

Reference: OpenClaw documentation describes skills as folders containing `SKILL.md` and lists common workspace and user-level skill roots.

## Manual Script Usage

```bash
python3 scripts/build_source_pack.py /path/to/course-folder
```

Useful options:

```bash
python3 scripts/build_source_pack.py /path/to/course-folder --run-id stable-run
python3 scripts/build_source_pack.py /path/to/course-folder --vault-dir /path/to/ObsidianVault
python3 scripts/build_source_pack.py /path/to/course-folder --no-install
```

`--no-install` disables automatic dependency installation. Use it only if you have already installed the required packages in the active Python environment.

## Safety Notes

- The script does not upload course materials.
- The script does not render every slide into screenshots.
- The script writes extracted intermediate files under `.course-exam-note/<run-id>/`.
- The script writes extracted image assets under `assets/course-exam-note/<run-id>/`.
- The script may install Python dependencies into `~/.codex/cache/course-exam-note/venv` on first run.

## License

No license has been declared yet. Add one before publishing this as an open-source package intended for external reuse.
