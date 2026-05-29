# Course Exam Note Policy

Use this policy after `scripts/build_source_pack.py` has produced a source pack.

## Final Note Shape

Create one Obsidian Markdown note. The note must focus on chapter-level knowledge, not PPT filenames or slide numbers.

Required sections:

1. `# 课程总览`
2. `# 期末复习路线`
3. `# 按章节整理的完整知识点`
4. `# 易错点与记忆提示`
5. `# 待人工复核的复杂图示页`

Do not create a standalone `核心术语表` section. Do not include a PPT coverage index in the final note.

## Coverage Rule

Treat PPTX as the primary coverage source. Every extracted title, bullet, table cell, speaker note, alt text, and XML text node must be represented in the chapter knowledge sections or intentionally merged into a broader explanation.

Use `coverage.json` only as an internal audit artifact. It must not be pasted into the final note.

## Translation Rule

Translate English slide content into rigorous Chinese. Use the Chinese PDF textbook to choose professional terminology and to clarify inaccurate or vague slides.

When an important term first appears in the body, write it as:

`中文术语（English term）`

After first mention, use the Chinese term unless the English term prevents ambiguity. Keep textbook-based additions concise and exam-oriented.

## Image Rule

Insert important image resources inside the relevant chapter subsection, close to the paragraph they explain. Good candidates include tables, process diagrams, architecture diagrams, schema diagrams, comparison figures, formulas, and screenshots that contain semantic content.

Do not collect images at the end. Do not insert decorative images, logos, repeated backgrounds, or purely aesthetic assets.

Use Obsidian wiki embeds:

`![[assets/course-exam-note/<run-id>/ppt-media/example.png]]`

For important tables that are extractable as text, prefer Markdown tables. If the table is only available as an image, embed the image and summarize its key exam point nearby.

## Visual Review Rule

The workflow does not render every slide. If `visual_review.md` lists a slide, add a short callout near the corresponding knowledge point:

`> [!warning] 该知识点在课件中包含复杂图示，已提取文字内容，建议复核原始 PPT 的视觉关系。`

Do not over-explain visual-review warnings. The main note should stay useful for learning and memory.

## Writing Style

Write for a student who did not attend the course and is preparing for a final exam from zero.

Prefer:

- Clear chapter hierarchy.
- Definitions followed by examples.
- Short comparison tables.
- Exam-oriented misconceptions and memory cues.
- Concise textbook supplements when PPT explanations are weak.

Avoid:

- Slide-by-slide dumps.
- Long textbook rewriting.
- Unverified additions not grounded in PPTX/PDF content.
- Separate term glossaries.
