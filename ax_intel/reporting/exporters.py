from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
_FONT_REGULAR = _FONT_DIR / "NanumGothic-Regular.ttf"
_FONT_BOLD = _FONT_DIR / "NanumGothic-Bold.ttf"


def _is_heading(raw: str) -> int:
    """Return heading level (1-6) or 0 if not a heading."""
    m = re.match(r"^(#{1,6})\s", raw.strip())
    return len(m.group(1)) if m else 0


def _is_separator(raw: str) -> bool:
    return raw.strip().startswith("---")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.lstrip("#> -").strip()


def _plain_lines(markdown: str) -> list[str]:
    lines = []
    for raw in markdown.splitlines():
        clean = _strip_markdown(raw)
        if clean:
            lines.append(clean)
    return lines


# ── DOCX ──────────────────────────────────────────────────────────────────────

def write_docx(path: Path, markdown: str) -> None:
    paragraphs_xml = []
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if not stripped or _is_separator(stripped):
            continue
        h = _is_heading(raw_line)
        text = xml_escape(_strip_markdown(stripped))
        if not text:
            continue
        size = str(28 if h == 1 else 24 if h == 2 else 22 if h >= 3 else 20)
        bold_tag = "<w:b/>" if h else ""
        color_tag = '<w:color w:val="1e3a5f"/>' if h == 2 else ""
        para = (
            f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>'
            f'<w:r><w:rPr>{bold_tag}{color_tag}'
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
            f"<w:t>{text}</w:t></w:r></w:p>"
        )
        paragraphs_xml.append(para)

    body = "\n".join(paragraphs_xml)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>
    </w:sectPr>
  </w:body>
</w:document>"""
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as arc:
        arc.writestr("[Content_Types].xml", content_types)
        arc.writestr("_rels/.rels", rels)
        arc.writestr("word/document.xml", document_xml)


# ── PDF (fpdf2 + NanumGothic) ─────────────────────────────────────────────────

def write_pdf(path: Path, markdown: str) -> None:
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=20, top=20, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # 폰트 등록
    if _FONT_REGULAR.exists():
        pdf.add_font("Nanum", "", str(_FONT_REGULAR))
        pdf.add_font("Nanum", "B", str(_FONT_BOLD))
        font_name = "Nanum"
    else:
        font_name = "Helvetica"

    pdf.add_page()

    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()

        # 빈 줄
        if not stripped:
            pdf.ln(3)
            continue

        # 구분선
        if _is_separator(stripped):
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)
            continue

        h = _is_heading(raw_line)
        text = _strip_markdown(stripped)
        if not text:
            continue

        # 스타일 설정
        if h == 1:
            pdf.set_font(font_name, "B", 16)
            pdf.set_text_color(17, 24, 39)
            pdf.ln(4)
        elif h == 2:
            pdf.set_font(font_name, "B", 13)
            pdf.set_text_color(30, 58, 95)
            pdf.ln(3)
        elif h >= 3:
            pdf.set_font(font_name, "B", 11)
            pdf.set_text_color(55, 65, 81)
            pdf.ln(2)
        elif stripped.startswith(("- ", "* ")):
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(31, 41, 55)
            text = "• " + text
        else:
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(31, 41, 55)

        pdf.multi_cell(w=170, h=6, text=text)

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
