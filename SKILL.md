---
name: course-exam-note
description: Build complete Chinese Obsidian final-exam study notes from a folder of course PPTX slides and Chinese PDF textbook materials. Use when Codex needs to scan PPTX/PDF course files, extract all slide text/tables/notes/original images without bulk slide screenshots, translate English slides with professional terminology, supplement unclear slides from a Chinese textbook, and write a chapter-centered Markdown note through Obsidian MCP.
---

# Course Exam Note

## Overview

Use this skill to turn a course folder containing English `.pptx` slides and a Chinese `.pdf` textbook into one detailed, chapter-centered Obsidian Markdown note for final-exam study.

The final note must emphasize complete chapter knowledge summaries. Do not create a standalone core terminology section, and do not include a PPT coverage index in the final note.

## Workflow

1. Inspect the current folder and confirm it contains course `.pptx` and `.pdf` files.
2. Run the source-pack builder:

   ```bash
   python3 /Users/bytedance/.codex/skills/course-exam-note/scripts/build_source_pack.py <course-folder>
   ```

3. Open the generated artifacts in `.course-exam-note/<run-id>/`:
   - `source_pack.json`: structured PPTX/PDF extraction data.
   - `raw_slides.md`: readable PPTX extraction, including slide text, tables, notes, image candidates, and visual-review warnings.
   - `raw_textbook.md`: extracted Chinese textbook text and PDF image candidates.
   - `visual_review.md`: complex PPT visual pages that were not screenshot-rendered.
   - `coverage.json`: internal audit only; never paste it into the final note.
   - `generation_prompt.md`: ready-to-use generation instructions for the final note.
4. Read `references/note_policy.md` before writing the final note.
5. Generate the final Chinese Markdown note and write it to Obsidian through the Obsidian MCP tools.

## Extraction Rules

The script extracts PPTX data without rendering every slide:

- All XML text nodes, titles, bullets, table text, speaker notes, and image alt text.
- Original embedded PPT images from `ppt/media`, mapped back to their slides.
- PDF page text and large PDF image candidates.
- Complex visual-slide flags for SmartArt, dense connectors, grouped shapes, and graphic-frame-heavy pages.

The script creates a dedicated venv under `~/.codex/cache/course-exam-note/venv` and installs `python-pptx`, `PyMuPDF`, `Pillow`, and `lxml` if they are missing. Use `--no-install` only when dependency installation is explicitly not allowed.

## Note Writing Rules

Use the generated source pack as grounding evidence. PPTX is the coverage source; the Chinese PDF textbook is the terminology and clarification source.

Final note structure:

1. `# 课程总览`
2. `# 期末复习路线`
3. `# 按章节整理的完整知识点`
4. `# 易错点与记忆提示`
5. `# 待人工复核的复杂图示页`

Hard requirements:

- Organize by chapters and knowledge points, not by PPT filenames or slide pages.
- Cover every extracted PPT knowledge point in the chapter sections.
- Translate English slide content into rigorous Chinese.
- Mark important terms at first use as `中文术语（English term）`.
- Keep textbook-based supplements short and exam-oriented.
- Insert important tables, process diagrams, schema diagrams, architecture diagrams, and other semantic images near the relevant knowledge point.
- Do not insert decorative images, repeated logos, or purely aesthetic assets.
- Do not create a standalone `核心术语表`.
- Do not include a PPT coverage index in the final note.

For complex visual pages listed in `visual_review.md`, add a short callout near the matching knowledge point:

```markdown
> [!warning] 该知识点在课件中包含复杂图示，已提取文字内容，建议复核原始 PPT 的视觉关系。
```

## Obsidian Output

Default final note path:

```text
期末复习/<资料文件夹名> 期末复习总笔记.md
```

Default attachment paths:

```text
assets/course-exam-note/<run-id>/ppt-media/
assets/course-exam-note/<run-id>/pdf-media/
```

Use Obsidian wiki embeds for images:

```markdown
![[assets/course-exam-note/<run-id>/ppt-media/example.png]]
```

If Obsidian MCP is available, write the note with `obsidian_patch_note` or the available note-write operation. If the course folder is not inside an Obsidian vault, use the nearest vault discovered by the script or ask the user for the target vault before writing.

## Validation Checklist

Before finishing:

- Confirm the source-pack script ran successfully and reported PPTX/PDF counts.
- Confirm `source_pack.json` has one record per extracted PPT slide.
- Confirm the final note has no standalone core terminology section.
- Confirm the final note has no PPT coverage index.
- Confirm important image embeds appear inside relevant chapter knowledge sections.
- Confirm `visual_review.md` items are represented as concise review callouts.
- Confirm the final note was written to or prepared for Obsidian.
