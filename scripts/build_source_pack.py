#!/usr/bin/env python3
"""
Build a structured source pack from course PPTX and PDF files.

The script extracts every readable PPTX slide text node, tables, notes,
original embedded images, PDF page text, selected PDF images, and internal
coverage/visual-review artifacts. It deliberately does not render every slide
as an image.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import textwrap
import venv
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


REQUIRED_MODULES = {
    "pptx": "python-pptx",
    "fitz": "PyMuPDF",
    "PIL": "Pillow",
    "lxml": "lxml",
}

SKILL_NAME = "course-exam-note"
SKIP_DIRS = {".git", ".obsidian", ".course-exam-note", "assets", "__MACOSX"}
IMAGE_MIN_AREA = 40_000
IMAGE_MIN_EDGE = 120


def ensure_dependencies() -> None:
    if "--no-install" in sys.argv:
        return

    cache_dir = Path.home() / ".codex" / "cache" / SKILL_NAME
    venv_dir = cache_dir / "venv"
    python_bin = venv_dir / "bin" / "python"
    in_target_venv = Path(sys.prefix).resolve() == venv_dir.resolve()

    if not in_target_venv:
        if not python_bin.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"[{SKILL_NAME}] creating venv at {venv_dir}", file=sys.stderr)
            venv.EnvBuilder(with_pip=True).create(venv_dir)
        os.execve(str(python_bin), [str(python_bin), __file__, *sys.argv[1:]], os.environ.copy())

    missing = [pip_name for module, pip_name in REQUIRED_MODULES.items() if importlib.util.find_spec(module) is None]
    if not missing:
        return

    install_cmd = [sys.executable, "-m", "pip", "install", *sorted(set(missing))]
    print(f"[{SKILL_NAME}] installing missing packages: {', '.join(sorted(set(missing)))}", file=sys.stderr)
    subprocess.check_call(install_cmd)


ensure_dependencies()

try:
    import fitz  # type: ignore
    from lxml import etree  # type: ignore
    from PIL import Image  # type: ignore
except Exception as exc:  # pragma: no cover - defensive failure message
    raise SystemExit(
        "Required packages are unavailable. Re-run without --no-install, or install: "
        "python-pptx PyMuPDF Pillow lxml"
    ) from exc


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class OutputPaths:
    source_dir: Path
    vault_dir: Path | None
    work_dir: Path
    asset_dir: Path
    obsidian_asset_prefix: str
    run_id: str


def local_name(node: Any) -> str:
    return etree.QName(node).localname


def clean_text(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def unique_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = clean_text(item)
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "-", path.stem)
    return stem.strip("-") or "course"


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_vault(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".obsidian").is_dir():
            return candidate
    return None


def make_paths(source_dir: Path, output_dir: Path | None, vault_dir: Path | None, run_id: str | None) -> OutputPaths:
    source_dir = source_dir.resolve()
    resolved_vault = vault_dir.resolve() if vault_dir else discover_vault(source_dir)
    run = run_id or _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    work_dir = (output_dir.resolve() if output_dir else source_dir / ".course-exam-note") / run
    asset_base = resolved_vault if resolved_vault else source_dir
    asset_dir = asset_base / "assets" / SKILL_NAME / run
    prefix = f"assets/{SKILL_NAME}/{run}"
    work_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(source_dir, resolved_vault, work_dir, asset_dir, prefix, run)


def iter_source_files(source_dir: Path) -> tuple[list[Path], list[Path]]:
    pptx_files: list[Path] = []
    pdf_files: list[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(source_dir).parts):
            continue
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".pptx" and not path.name.startswith("~$"):
            pptx_files.append(path)
        elif suffix == ".pdf":
            pdf_files.append(path)
    return pptx_files, pdf_files


def zip_read_xml(zf: zipfile.ZipFile, name: str) -> Any | None:
    try:
        return etree.fromstring(zf.read(name))
    except KeyError:
        return None


def sorted_slide_names(zf: zipfile.ZipFile) -> list[str]:
    names = [
        name
        for name in zf.namelist()
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
    ]
    return sorted(names, key=lambda value: int(re.search(r"slide(\d+)\.xml", value).group(1)))  # type: ignore[union-attr]


def collect_all_text(root: Any | None) -> list[str]:
    if root is None:
        return []
    texts = [node.text or "" for node in root.xpath(".//*[local-name()='t']")]
    return unique_preserve(texts)


def collect_paragraphs(root: Any | None) -> list[str]:
    if root is None:
        return []
    paragraphs: list[str] = []
    for paragraph in root.xpath(".//*[local-name()='p']"):
        text = clean_text("".join(paragraph.xpath(".//*[local-name()='t']/text()")))
        if text:
            paragraphs.append(text)
    return unique_preserve(paragraphs)


def collect_tables(root: Any | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    tables: list[dict[str, Any]] = []
    for tbl_index, tbl in enumerate(root.xpath(".//*[local-name()='tbl']"), start=1):
        rows: list[list[str]] = []
        for tr in tbl.xpath("./*[local-name()='tr']"):
            row: list[str] = []
            for tc in tr.xpath("./*[local-name()='tc']"):
                row.append(clean_text(" ".join(tc.xpath(".//*[local-name()='t']/text()"))))
            if any(row):
                rows.append(row)
        if rows:
            tables.append({"index": tbl_index, "rows": rows})
    return tables


def collect_relationships(zf: zipfile.ZipFile, rels_name: str) -> dict[str, str]:
    root = zip_read_xml(zf, rels_name)
    if root is None:
        return {}
    relationships: dict[str, str] = {}
    base_dir = str(PurePosixPath(rels_name).parent.parent)
    for rel in root.xpath(".//*[local-name()='Relationship']"):
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if not rel_id or not target:
            continue
        if target.startswith("/"):
            normalized = target.lstrip("/")
        else:
            normalized = posixpath.normpath(str(PurePosixPath(base_dir) / target))
        relationships[rel_id] = normalized
    return relationships


def image_size(blob: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(blob)) as img:
            return img.size
    except Exception:
        return None, None


def is_large_image(width: int | None, height: int | None) -> bool:
    if width is None or height is None:
        return False
    return width * height >= IMAGE_MIN_AREA and width >= IMAGE_MIN_EDGE and height >= IMAGE_MIN_EDGE


def copy_zip_image(
    zf: zipfile.ZipFile,
    media_path: str,
    destination: Path,
    obsidian_path: str,
) -> dict[str, Any]:
    blob = zf.read(media_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    width, height = image_size(blob)
    return {
        "source": media_path,
        "file": str(destination),
        "obsidian_path": obsidian_path,
        "width": width,
        "height": height,
        "important_candidate": is_large_image(width, height),
    }


def collect_slide_images(
    zf: zipfile.ZipFile,
    root: Any | None,
    rels: dict[str, str],
    pptx_path: Path,
    slide_index: int,
    out: OutputPaths,
) -> list[dict[str, Any]]:
    if root is None:
        return []
    images: list[dict[str, Any]] = []
    for image_index, pic in enumerate(root.xpath(".//*[local-name()='pic']"), start=1):
        c_nv_pr = pic.xpath(".//*[local-name()='cNvPr']")
        blips = pic.xpath(".//*[local-name()='blip']")
        embed_id = None
        for blip in blips:
            embed_id = blip.get(f"{{{NS['r']}}}embed") or blip.get(f"{{{NS['r']}}}link")
            if embed_id:
                break
        media_path = rels.get(embed_id or "")
        if not media_path or not media_path.startswith("ppt/media/"):
            continue
        ext = Path(media_path).suffix.lower() or ".bin"
        file_name = f"{safe_stem(pptx_path)}-slide-{slide_index:03d}-image-{image_index:02d}{ext}"
        obsidian_path = f"{out.obsidian_asset_prefix}/ppt-media/{file_name}"
        destination = out.asset_dir / "ppt-media" / file_name
        image_info = copy_zip_image(zf, media_path, destination, obsidian_path)
        image_info.update(
            {
                "index": image_index,
                "name": c_nv_pr[0].get("name") if c_nv_pr else "",
                "description": c_nv_pr[0].get("descr") if c_nv_pr else "",
                "embed_id": embed_id,
            }
        )
        images.append(image_info)
    return images


def slide_complexity(root: Any | None, text_lines: list[str], images: list[dict[str, Any]]) -> dict[str, Any]:
    if root is None:
        return {"needs_visual_review": False, "reasons": []}
    counts = {
        "shape_count": len(root.xpath(".//*[local-name()='sp']")),
        "connector_count": len(root.xpath(".//*[local-name()='cxnSp']")),
        "group_shape_count": len(root.xpath(".//*[local-name()='grpSp']")),
        "graphic_frame_count": len(root.xpath(".//*[local-name()='graphicFrame']")),
        "picture_count": len(root.xpath(".//*[local-name()='pic']")),
        "diagram_marker_count": len(root.xpath(".//*[contains(name(), 'dgm') or contains(@uri, 'diagram')]")),
    }
    reasons: list[str] = []
    if counts["connector_count"] >= 3:
        reasons.append("connector-dense")
    if counts["group_shape_count"] >= 1 and counts["shape_count"] >= 8:
        reasons.append("grouped-shapes")
    if counts["graphic_frame_count"] >= 2 and counts["shape_count"] >= 8:
        reasons.append("graphic-frame-dense")
    if counts["diagram_marker_count"] > 0:
        reasons.append("smartart-or-diagram")
    if counts["shape_count"] >= 14 and len(text_lines) <= 5:
        reasons.append("many-shapes-low-text")
    if len(images) >= 3 and len(text_lines) <= 4:
        reasons.append("image-heavy-low-text")
    return {
        **counts,
        "needs_visual_review": bool(reasons),
        "reasons": reasons,
    }


def extract_notes(zf: zipfile.ZipFile, slide_name: str, slide_index: int) -> list[str]:
    rels_name = f"ppt/slides/_rels/{Path(slide_name).name}.rels"
    rels = collect_relationships(zf, rels_name)
    note_path = None
    for target in rels.values():
        if target.startswith("ppt/notesSlides/notesSlide") and target.endswith(".xml"):
            note_path = target
            break
    if not note_path:
        guessed = f"ppt/notesSlides/notesSlide{slide_index}.xml"
        if guessed in zf.namelist():
            note_path = guessed
    return collect_paragraphs(zip_read_xml(zf, note_path)) if note_path else []


def extract_pptx(pptx_path: Path, out: OutputPaths) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(pptx_path),
        "name": pptx_path.name,
        "sha1": file_sha1(pptx_path),
        "slides": [],
        "errors": [],
    }
    try:
        with zipfile.ZipFile(pptx_path) as zf:
            for slide_index, slide_name in enumerate(sorted_slide_names(zf), start=1):
                root = zip_read_xml(zf, slide_name)
                rels = collect_relationships(zf, f"ppt/slides/_rels/{Path(slide_name).name}.rels")
                paragraphs = collect_paragraphs(root)
                all_text = collect_all_text(root)
                tables = collect_tables(root)
                notes = extract_notes(zf, slide_name, slide_index)
                images = collect_slide_images(zf, root, rels, pptx_path, slide_index, out)
                image_alt_texts = unique_preserve(
                    value
                    for image in images
                    for value in [image.get("description") or "", image.get("name") or ""]
                )
                title = paragraphs[0] if paragraphs else (all_text[0] if all_text else f"Slide {slide_index}")
                complexity = slide_complexity(root, paragraphs or all_text, images)
                slide = {
                    "slide_index": slide_index,
                    "slide_xml": slide_name,
                    "title": title,
                    "paragraphs": paragraphs,
                    "all_text": all_text,
                    "tables": tables,
                    "notes": notes,
                    "image_alt_texts": image_alt_texts,
                    "images": images,
                    "complexity": complexity,
                    "text_char_count": sum(len(item) for item in all_text) + sum(len(item) for item in notes) + sum(len(item) for item in image_alt_texts),
                    "status": "needs_visual_review" if complexity["needs_visual_review"] else "covered",
                }
                result["slides"].append(slide)
    except Exception as exc:
        result["errors"].append(str(exc))
    return result


def extract_pdf(pdf_path: Path, out: OutputPaths) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(pdf_path),
        "name": pdf_path.name,
        "sha1": file_sha1(pdf_path),
        "pages": [],
        "errors": [],
    }
    try:
        doc = fitz.open(pdf_path)
        seen_images: set[int] = set()
        for page_index, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            images: list[dict[str, Any]] = []
            for image_index, image in enumerate(page.get_images(full=True), start=1):
                xref = image[0]
                if xref in seen_images:
                    continue
                extracted = doc.extract_image(xref)
                width = extracted.get("width")
                height = extracted.get("height")
                if not is_large_image(width, height):
                    continue
                seen_images.add(xref)
                ext = "." + extracted.get("ext", "bin").lower()
                file_name = f"{safe_stem(pdf_path)}-page-{page_index:03d}-image-{image_index:02d}{ext}"
                obsidian_path = f"{out.obsidian_asset_prefix}/pdf-media/{file_name}"
                destination = out.asset_dir / "pdf-media" / file_name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(extracted["image"])
                images.append(
                    {
                        "index": image_index,
                        "xref": xref,
                        "file": str(destination),
                        "obsidian_path": obsidian_path,
                        "width": width,
                        "height": height,
                        "important_candidate": True,
                    }
                )
            result["pages"].append(
                {
                    "page_index": page_index,
                    "text": text,
                    "text_char_count": len(text),
                    "images": images,
                }
            )
        doc.close()
    except Exception as exc:
        result["errors"].append(str(exc))
    return result


def markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_raw_slides(pack: dict[str, Any], path: Path) -> None:
    lines = ["# Raw PPTX Source", ""]
    for deck in pack["pptx"]:
        lines.extend([f"## {deck['name']}", ""])
        if deck["errors"]:
            lines.extend(["> [!warning] Extraction errors: " + "; ".join(deck["errors"]), ""])
        for slide in deck["slides"]:
            lines.extend([f"### Slide {slide['slide_index']}: {slide['title']}", ""])
            if slide["complexity"]["needs_visual_review"]:
                reasons = ", ".join(slide["complexity"]["reasons"])
                lines.extend([f"> [!warning] 该页包含复杂图示，建议人工复核视觉关系。原因：{reasons}", ""])
            if slide["paragraphs"]:
                lines.extend(["#### Text", ""])
                lines.extend([f"- {item}" for item in slide["paragraphs"]])
                lines.append("")
            if slide["tables"]:
                lines.extend(["#### Tables", ""])
                for table in slide["tables"]:
                    lines.append(markdown_table(table["rows"]))
                    lines.append("")
            if slide["notes"]:
                lines.extend(["#### Notes", ""])
                lines.extend([f"- {item}" for item in slide["notes"]])
                lines.append("")
            if slide.get("image_alt_texts"):
                lines.extend(["#### Image alt text", ""])
                lines.extend([f"- {item}" for item in slide["image_alt_texts"]])
                lines.append("")
            important_images = [img for img in slide["images"] if img["important_candidate"]]
            if important_images:
                lines.extend(["#### Important image candidates", ""])
                for image in important_images:
                    alt = image.get("description") or image.get("name") or f"slide {slide['slide_index']} image"
                    lines.append(f"![[{image['obsidian_path']}|{alt}]]")
                lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_raw_textbook(pack: dict[str, Any], path: Path) -> None:
    lines = ["# Raw PDF Textbook Source", ""]
    for pdf in pack["pdf"]:
        lines.extend([f"## {pdf['name']}", ""])
        if pdf["errors"]:
            lines.extend(["> [!warning] Extraction errors: " + "; ".join(pdf["errors"]), ""])
        for page in pdf["pages"]:
            lines.extend([f"### Page {page['page_index']}", ""])
            if page["text"]:
                lines.append(page["text"])
                lines.append("")
            if page["images"]:
                lines.extend(["#### Image candidates", ""])
                for image in page["images"]:
                    lines.append(f"![[{image['obsidian_path']}]]")
                lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_coverage(pack: dict[str, Any], json_path: Path, md_path: Path) -> None:
    coverage = {
        "run_id": pack["run_id"],
        "pptx": [],
        "summary": {
            "pptx_file_count": len(pack["pptx"]),
            "slide_count": 0,
            "needs_visual_review_count": 0,
        },
    }
    lines = ["# Internal PPTX Coverage Audit", ""]
    for deck in pack["pptx"]:
        deck_item = {"name": deck["name"], "path": deck["path"], "slides": []}
        lines.extend([f"## {deck['name']}", ""])
        for slide in deck["slides"]:
            coverage["summary"]["slide_count"] += 1
            if slide["status"] == "needs_visual_review":
                coverage["summary"]["needs_visual_review_count"] += 1
            item = {
                "slide_index": slide["slide_index"],
                "title": slide["title"],
                "text_char_count": slide["text_char_count"],
                "table_count": len(slide["tables"]),
                "image_count": len(slide["images"]),
                "status": slide["status"],
                "visual_review_reasons": slide["complexity"]["reasons"],
            }
            deck_item["slides"].append(item)
            reason = ""
            if item["visual_review_reasons"]:
                reason = " (" + ", ".join(item["visual_review_reasons"]) + ")"
            lines.append(
                f"- Slide {item['slide_index']}: {item['title']} - {item['status']}, "
                f"text={item['text_char_count']}, tables={item['table_count']}, images={item['image_count']}{reason}"
            )
        lines.append("")
        coverage["pptx"].append(deck_item)
    json_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_visual_review(pack: dict[str, Any], path: Path) -> None:
    lines = ["# Visual Review Queue", ""]
    found = False
    for deck in pack["pptx"]:
        for slide in deck["slides"]:
            if slide["status"] != "needs_visual_review":
                continue
            found = True
            lines.extend(
                [
                    f"## {deck['name']} - Slide {slide['slide_index']}: {slide['title']}",
                    "",
                    "- Reasons: " + ", ".join(slide["complexity"]["reasons"]),
                    "- Use the original PPTX if this visual relationship is exam-relevant.",
                    "",
                ]
            )
    if not found:
        lines.append("No complex visual slides were detected.")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_generation_prompt(pack: dict[str, Any], path: Path) -> None:
    note_path = pack["recommended_note_path"]
    prompt = f"""
    请基于同目录下的 raw_slides.md、raw_textbook.md、source_pack.json 和 visual_review.md 生成 Obsidian Markdown 期末复习总笔记。

    输出目标：{note_path}

    生成要求：
    - 最终笔记以“按章节整理的完整知识点”为核心，不按 PPT 页码机械罗列。
    - 不生成独立“核心术语表”，不在最终笔记中加入 PPT 覆盖索引。
    - 英文课件内容翻译为严谨中文；专业术语首次出现时写为“中文术语（English term）”。
    - PPT 中所有可抽取知识点必须并入对应章节知识点。
    - 中文 PDF 教材用于校正术语、补足 PPT 不清楚或不准确处；补充说明保持短小。
    - 重要表格、流程图、结构图等图片候选要插入对应知识点附近；装饰图不要插入。
    - 对 visual_review.md 中的复杂图示，在对应章节写简短 Obsidian warning callout，提示复核原始 PPT 视觉关系。
    """
    path.write_text(textwrap.dedent(prompt).strip() + "\n", encoding="utf-8")


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    source_dir = Path(args.source_dir)
    out = make_paths(source_dir, Path(args.output_dir) if args.output_dir else None, Path(args.vault_dir) if args.vault_dir else None, args.run_id)
    pptx_files, pdf_files = iter_source_files(out.source_dir)
    pptx_results = [extract_pptx(path, out) for path in pptx_files]
    pdf_results = [extract_pdf(path, out) for path in pdf_files]
    note_file_name = f"{out.source_dir.name} 期末复习总笔记.md"
    recommended_note_path = f"期末复习/{note_file_name}"
    pack = {
        "schema": "course-exam-note.source-pack.v1",
        "run_id": out.run_id,
        "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(out.source_dir),
        "vault_dir": str(out.vault_dir) if out.vault_dir else None,
        "work_dir": str(out.work_dir),
        "asset_dir": str(out.asset_dir),
        "obsidian_asset_prefix": out.obsidian_asset_prefix,
        "recommended_note_path": recommended_note_path,
        "pptx": pptx_results,
        "pdf": pdf_results,
    }
    source_pack_path = out.work_dir / "source_pack.json"
    source_pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    write_raw_slides(pack, out.work_dir / "raw_slides.md")
    write_raw_textbook(pack, out.work_dir / "raw_textbook.md")
    write_coverage(pack, out.work_dir / "coverage.json", out.work_dir / "coverage.md")
    write_visual_review(pack, out.work_dir / "visual_review.md")
    write_generation_prompt(pack, out.work_dir / "generation_prompt.md")
    return pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a course exam note source pack from PPTX and PDF files.")
    parser.add_argument("source_dir", nargs="?", default=".", help="Folder containing PPTX and PDF course materials.")
    parser.add_argument("--output-dir", help="Directory for .course-exam-note run artifacts. Defaults to SOURCE/.course-exam-note.")
    parser.add_argument("--vault-dir", help="Obsidian vault root. Defaults to nearest parent containing .obsidian.")
    parser.add_argument("--run-id", help="Stable run id for reproducible output paths.")
    parser.add_argument("--no-install", action="store_true", help="Do not auto-create a venv or install missing Python packages.")
    args = parser.parse_args()

    pack = build_pack(args)
    print(json.dumps(
        {
            "run_id": pack["run_id"],
            "work_dir": pack["work_dir"],
            "asset_dir": pack["asset_dir"],
            "recommended_note_path": pack["recommended_note_path"],
            "pptx_files": len(pack["pptx"]),
            "pdf_files": len(pack["pdf"]),
            "slides": sum(len(deck["slides"]) for deck in pack["pptx"]),
            "pdf_pages": sum(len(pdf["pages"]) for pdf in pack["pdf"]),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
