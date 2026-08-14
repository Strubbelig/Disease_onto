from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript.md"
OUTPUT = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript.docx"
FIGURE_2_OUTPUT = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript_with_Figure_2.docx"
TABLE_GEOMETRY_DIR = Path(
    "/Users/Strubbelig/.codex/plugins/cache/openai-primary-runtime/documents/"
    "26.812.11052/skills/documents/scripts"
)
sys.path.insert(0, str(TABLE_GEOMETRY_DIR))
from table_geometry import apply_table_geometry  # noqa: E402


FONT = "Arial"
BLACK = RGBColor(0, 0, 0)
GRAY = RGBColor(89, 89, 89)
LIGHT_GRAY = "E7E6E6"
RULE_GRAY = "BFBFBF"


def set_run_font(run, size=11, bold=None, italic=None, color=BLACK, superscript=False):
    run.font.name = FONT
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), FONT)
    run.font.size = Pt(size)
    run.font.color.rgb = color
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if superscript:
        run.font.superscript = True
    return run


def add_hyperlink(paragraph, text, url, *, bold=False, italic=False, size=11):
    rid = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rfonts = OxmlElement("w:rFonts")
    rfonts.set(qn("w:ascii"), FONT)
    rfonts.set(qn("w:hAnsi"), FONT)
    rpr.append(rfonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rpr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    size_el = OxmlElement("w:sz")
    size_el.set(qn("w:val"), str(int(size * 2)))
    rpr.append(size_el)
    if bold:
        rpr.append(OxmlElement("w:b"))
    if italic:
        rpr.append(OxmlElement("w:i"))
    run.append(rpr)
    text_el = OxmlElement("w:t")
    text_el.text = text
    run.append(text_el)
    link.append(run)
    paragraph._p.append(link)


TOKEN_RE = re.compile(r"(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def add_inline(paragraph, text, *, size=11, base_bold=False, base_italic=False, color=BLACK):
    pos = 0
    for match in TOKEN_RE.finditer(text):
        if match.start() > pos:
            add_plain_with_superscript(
                paragraph,
                text[pos : match.start()],
                size=size,
                bold=base_bold,
                italic=base_italic,
                color=color,
            )
        token = match.group(0)
        if token.startswith("["):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            add_hyperlink(paragraph, label, url, bold=base_bold, italic=base_italic, size=size)
        elif token.startswith("**"):
            add_plain_with_superscript(
                paragraph,
                token[2:-2],
                size=size,
                bold=True,
                italic=base_italic,
                color=color,
            )
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=size, bold=base_bold, italic=base_italic, color=color)
            run.font.name = "Courier New"
            run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Courier New")
            run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Courier New")
        else:
            add_plain_with_superscript(
                paragraph,
                token[1:-1],
                size=size,
                bold=base_bold,
                italic=True,
                color=color,
            )
        pos = match.end()
    if pos < len(text):
        add_plain_with_superscript(
            paragraph,
            text[pos:],
            size=size,
            bold=base_bold,
            italic=base_italic,
            color=color,
        )


def add_plain_with_superscript(paragraph, text, *, size, bold, italic, color):
    pos = 0
    for match in re.finditer(r"\^([0-9,]+)", text):
        if match.start() > pos:
            set_run_font(
                paragraph.add_run(text[pos : match.start()]),
                size=size,
                bold=bold,
                italic=italic,
                color=color,
            )
        set_run_font(
            paragraph.add_run(match.group(1)),
            size=max(8, size - 2),
            bold=bold,
            italic=italic,
            color=color,
            superscript=True,
        )
        pos = match.end()
    if pos < len(text):
        set_run_font(paragraph.add_run(text[pos:]), size=size, bold=bold, italic=italic, color=color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cannot_split = OxmlElement("w:cantSplit")
    tr_pr.append(cannot_split)


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, color=RULE_GRAY, size=4):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:color"), color)


def style_paragraph(paragraph, *, line=2.0, before=0, after=0, alignment=WD_ALIGN_PARAGRAPH.LEFT):
    fmt = paragraph.paragraph_format
    fmt.alignment = alignment
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    fmt.keep_together = False
    return paragraph


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    set_run_font(run, size=9, color=GRAY)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    display = OxmlElement("w:t")
    display.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, display, end])


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.49)
    section.footer_distance = Inches(0.49)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:ascii"), FONT)
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    normal.font.size = Pt(11)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    normal.paragraph_format.space_after = Pt(0)

    for name, size, before, after, italic in [
        ("Heading 1", 14, 12, 6, False),
        ("Heading 2", 12, 10, 4, False),
        ("Heading 3", 11, 8, 2, True),
    ]:
        style = styles[name]
        style.font.name = FONT
        style._element.rPr.rFonts.set(qn("w:ascii"), FONT)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.italic = italic
        style.font.color.rgb = BLACK
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.keep_with_next = True

    footer = section.footer
    add_page_number(footer.paragraphs[0])
    doc.core_properties.title = "How Is Disease Formally Modelled in Biomedical Ontologies?"
    doc.core_properties.author = "Moritz Milewski; Martin Boeker"
    doc.core_properties.subject = "Systematic cross-sectional evaluation of ontology artifacts"
    doc.core_properties.keywords = "disease; biomedical ontology; ontology evaluation; semantic interoperability"


def add_title(doc, text):
    p = doc.add_paragraph()
    style_paragraph(p, line=1.0, after=14, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    set_run_font(p.add_run(text), size=16, bold=True)
    p.paragraph_format.keep_with_next = True


def add_heading(doc, text, level):
    p = doc.add_paragraph(style=f"Heading {level}")
    add_inline(p, text, size={1: 14, 2: 12, 3: 11}[level], base_bold=True, base_italic=(level == 3))
    return p


def add_body(doc, text, *, front=False, quoted=False):
    p = doc.add_paragraph()
    if front:
        style_paragraph(p, line=1.0, after=4)
        size = 10.5
    elif quoted:
        style_paragraph(p, line=1.15, after=3)
        p.paragraph_format.left_indent = Inches(0.25)
        size = 10
    else:
        style_paragraph(p, line=2.0)
        size = 11
    add_inline(p, text, size=size)
    return p


def add_list_item(doc, text, *, ordered=False, quoted=False):
    p = doc.add_paragraph(style="List Number" if ordered else "List Bullet")
    style_paragraph(p, line=1.15 if quoted else 2.0, after=2 if quoted else 0)
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    add_inline(p, text, size=10 if quoted else 11)
    return p


def add_markdown_table(doc, lines):
    parsed = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        parsed.append(cells)
    if len(parsed) < 2:
        return
    body = [parsed[0]] + parsed[2:]
    cols = len(body[0])
    doc.add_page_break()
    table = doc.add_table(rows=len(body), cols=cols)
    table.style = "Table Grid"
    for r_idx, values in enumerate(body):
        for c_idx, value in enumerate(values):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            style_paragraph(
                p,
                line=1.0,
                before=0,
                after=0,
                alignment=WD_ALIGN_PARAGRAPH.RIGHT if c_idx == cols - 1 else WD_ALIGN_PARAGRAPH.LEFT,
            )
            add_inline(p, value, size=9.5, base_bold=(r_idx == 0))
            set_cell_borders(cell)
            if r_idx == 0:
                shade_cell(cell, LIGHT_GRAY)
        if r_idx == 0:
            set_repeat_table_header(table.rows[r_idx])
        prevent_row_split(table.rows[r_idx])
    widths = [7600, 1760] if cols == 2 else [int(9360 / cols)] * cols
    widths[-1] += 9360 - sum(widths)
    apply_table_geometry(
        table,
        widths,
        table_width_dxa=9360,
        indent_dxa=120,
        cell_margins_dxa={"top": 80, "bottom": 80, "start": 120, "end": 120},
    )
    table.rows[0]._tr.get_or_add_trPr()
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_figure(doc, image_path, alt_text):
    if alt_text.startswith("Figure 2."):
        doc.add_page_break()
    p = doc.add_paragraph()
    style_paragraph(p, line=1.0, before=8, after=4, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = p.add_run()
    inline = run.add_picture(str(image_path), width=Inches(6.15))
    inline._inline.docPr.set("descr", alt_text)
    inline._inline.docPr.set("name", alt_text[:120])
    p.paragraph_format.keep_with_next = True


def build():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    doc = Document()
    configure_document(doc)

    in_front = True
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            add_title(doc, stripped[2:].strip())
            i += 1
            continue

        quoted = stripped.startswith(">")
        content = re.sub(r"^>\s?", "", stripped) if quoted else stripped

        if content.startswith("## "):
            heading = content[3:].strip()
            if heading == "Abstract":
                doc.add_page_break()
                in_front = False
            add_heading(doc, heading, 1)
            i += 1
            continue
        if content.startswith("### "):
            add_heading(doc, content[4:].strip(), 2)
            i += 1
            continue

        if content.startswith("!["):
            match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", content)
            if not match:
                raise ValueError(f"Could not parse image line: {content}")
            alt_text, relative_path = match.groups()
            add_figure(doc, SOURCE.parent / relative_path, alt_text)
            i += 1
            continue

        if content.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
            table_lines = [content]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            add_markdown_table(doc, table_lines)
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.*)$", content)
        bullet_match = re.match(r"^-\s+(.*)$", content)
        if ordered_match and (quoted or not in_front):
            add_list_item(doc, ordered_match.group(2), ordered=True, quoted=quoted)
        elif bullet_match:
            add_list_item(doc, bullet_match.group(1), ordered=False, quoted=quoted)
        else:
            p = add_body(doc, content, front=in_front, quoted=quoted)
            if in_front and content.startswith("**Moritz Milewski"):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if content.startswith("**Figure "):
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.keep_with_next = False
                if content.startswith("**Figure 2."):
                    doc.add_page_break()
        i += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    doc.save(FIGURE_2_OUTPUT)
    print(OUTPUT)
    print(FIGURE_2_OUTPUT)


if __name__ == "__main__":
    build()
