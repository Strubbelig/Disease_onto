from pathlib import Path
import shutil
import sys

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript_with_Figure_2.docx"
OUTPUT = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript_with_Figure_2_and_Synthesis_Table.docx"
CANONICAL = ROOT / "Scoping review" / "Disease_Ontology_Artifact_Evaluation_Manuscript.docx"
FIGURE_1 = ROOT / "Scoping review" / "Figures" / "artifact_selection_flow_diagram.png"
TABLE_GEOMETRY_DIR = Path(
    "/Users/Strubbelig/.codex/plugins/cache/openai-primary-runtime/documents/"
    "26.812.11052/skills/documents/scripts"
)
sys.path.insert(0, str(TABLE_GEOMETRY_DIR))
from table_geometry import apply_table_geometry  # noqa: E402


FONT = "Arial"
TEXT = RGBColor(0x20, 0x26, 0x2E)
HEADER_FILL = "315A79"
FIRST_COLUMN_FILL = "EAF0F4"
ALT_ROW_FILL = "F7F8F9"
BORDER = "C8CED3"


ROWS = [
    (
        "Disease-model category",
        "99/144 (69%) had no grounded model; 23 (16%) followed a BFO-aligned continuant route; 8 (6%) represented a process; 14 (10%) used state, quality, mixed, disorder, or unclear models.",
        "Most labels did not identify what kind of entity disease denotes; mappings require inspection of hierarchy and axioms.",
    ),
    (
        "Continuant versus occurrent",
        "90 (62%) made no commitment; 31 (22%) were continuants; 10 (7%) occurrents; 3 (2%) deliberate mixes; 10 (7%) unclear.",
        "A shared label can connect entities with incompatible temporal and identity conditions.",
    ),
    (
        "Grounding of pathologicality",
        "111 (77%) were undefined; 14 (10%) used primitive criteria; 11 (8%) evolutionary function; 7 (5%) normative or statistical grounding; 1 was not applicable.",
        "Top-level placement alone does not explain why a represented entity counts as pathological.",
    ),
    (
        "Reality versus classification",
        "61 (42%) denoted nosological categories; 45 (31%) biological states; 34 (24%) were unclear; 4 (3%) conflated these readings.",
        "Classification categories and patient-level biological entities should not be treated as interchangeable.",
    ),
    (
        "Crisp versus graded",
        "All 144 classes (100%) were silent.",
        "OWL class representation alone is not evidence for a philosophical commitment to crisp disease boundaries.",
    ),
    (
        "Evidence quality",
        "Only 10 definitions (7%) were good; 109 classes (76%) had poor or absent parentage; 2 classes (1%) achieved quality score 3.",
        "Sparse definitions and weak parentage limit interpretation, comparison, and reuse.",
    ),
    (
        "Foundational alignment",
        "BFO-aligned continuants had mean quality 1.91/3 and good parentage in 19/23 (83%); all 99 ungrounded classes scored 1/3.",
        "BFO plus a disease-specific pattern improved inspectability, although pathologicality often remained undefined.",
    ),
]


def set_repeat_header(row):
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
    shade = tc_pr.find(qn("w:shd"))
    if shade is None:
        shade = OxmlElement("w:shd")
        tc_pr.append(shade)
    shade.set(qn("w:fill"), fill)


def set_cell_borders(cell, *, top=False, bottom=False):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        enabled = (edge == "top" and top) or (edge == "bottom" and bottom)
        element.set(qn("w:val"), "single" if enabled else "nil")
        if enabled:
            element.set(qn("w:sz"), "8")
            element.set(qn("w:color"), "000000")


def style_run(run, *, bold=False, italic=False, white=False, size=8.5):
    run.font.name = FONT
    r_pr = run._element.get_or_add_rPr()
    r_pr.rFonts.set(qn("w:ascii"), FONT)
    r_pr.rFonts.set(qn("w:hAnsi"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(255, 255, 255) if white else TEXT


def write_cell(cell, text, *, header=False, first_column=False):
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.08
    run = paragraph.add_run(text)
    style_run(run, bold=header, size=8.5 if not header else 8.7)


def format_display_paragraph(paragraph, *, before=0, after=0, keep_with_next=False):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.keep_with_next = keep_with_next


def set_apa_number(paragraph, label):
    paragraph.text = ""
    format_display_paragraph(paragraph, before=8, after=0, keep_with_next=True)
    run = paragraph.add_run(label)
    style_run(run, bold=True, size=10.5)


def set_apa_title(paragraph, title):
    paragraph.text = ""
    format_display_paragraph(paragraph, before=0, after=5, keep_with_next=True)
    run = paragraph.add_run(title)
    style_run(run, italic=True, size=10.5)


def set_apa_note(paragraph, description):
    paragraph.text = ""
    format_display_paragraph(paragraph, before=5, after=6)
    label = paragraph.add_run("Note. ")
    style_run(label, italic=True, size=9.5)
    text_run = paragraph.add_run(description)
    style_run(text_run, size=9.5)


def insert_paragraph_before(element, document):
    from docx.text.paragraph import Paragraph

    paragraph_element = OxmlElement("w:p")
    element.addprevious(paragraph_element)
    return Paragraph(paragraph_element, document._body)


def insert_paragraph_after(element, document):
    from docx.text.paragraph import Paragraph

    paragraph_element = OxmlElement("w:p")
    element.addnext(paragraph_element)
    return Paragraph(paragraph_element, document._body)


def find_category_table(document):
    for table in document.tables:
        if table.rows and [cell.text.strip() for cell in table.rows[0].cells] == ["Disease-model category", "Classes"]:
            return table
    raise RuntimeError("Could not find the disease-model category table")


def build_table(document):
    table = document.add_table(rows=len(ROWS) + 1, cols=3)
    headings = ["Dimension", "Principal finding", "Interpretation for reuse"]
    for column, heading in enumerate(headings):
        cell = table.cell(0, column)
        write_cell(cell, heading, header=True)
        set_cell_borders(cell, top=True, bottom=True)
    set_repeat_header(table.rows[0])
    prevent_row_split(table.rows[0])

    for row_index, values in enumerate(ROWS, 1):
        for column, value in enumerate(values):
            cell = table.cell(row_index, column)
            write_cell(cell, value, first_column=(column == 0))
            set_cell_borders(cell, bottom=(row_index == len(ROWS)))
        prevent_row_split(table.rows[row_index])

    apply_table_geometry(
        table,
        [2100, 3860, 3400],
        table_width_dxa=9360,
        indent_dxa=120,
        cell_margins_dxa={"top": 95, "bottom": 95, "start": 120, "end": 120},
    )
    return table


def format_figure_apa(document, number, title, note):
    children = list(document.element.body.iterchildren())
    caption_index = next(
        (
            index
            for index, element in enumerate(children)
            if element.tag == qn("w:p") and paragraph_text(element).startswith(f"Figure {number}.")
        ),
        None,
    )
    if caption_index is None or caption_index == 0:
        raise RuntimeError(f"Could not locate Figure {number}")
    drawing = children[caption_index - 1]
    if not any(True for _ in drawing.iter(qn("w:drawing"))):
        raise RuntimeError(f"Expected the Figure {number} drawing immediately before its caption")

    from docx.text.paragraph import Paragraph

    title_paragraph = insert_paragraph_before(drawing, document)
    number_paragraph = insert_paragraph_before(title_paragraph._p, document)
    set_apa_number(number_paragraph, f"Figure {number}")
    set_apa_title(title_paragraph, title)
    note_paragraph = Paragraph(children[caption_index], document._body)
    set_apa_note(note_paragraph, note)


def replace_figure_image(document, number, image_path, *, width_inches=7.2):
    children = list(document.element.body.iterchildren())
    number_index = next(
        (
            index
            for index, element in enumerate(children)
            if element.tag == qn("w:p") and paragraph_text(element) == f"Figure {number}"
        ),
        None,
    )
    if number_index is None:
        raise RuntimeError(f"Could not locate Figure {number} number paragraph")
    drawing = next(
        (
            element
            for element in children[number_index + 1 : number_index + 4]
            if any(True for _ in element.iter(qn("w:drawing")))
        ),
        None,
    )
    if drawing is None:
        raise RuntimeError(f"Could not locate Figure {number} drawing")

    blip = next(drawing.iter(qn("a:blip")), None)
    if blip is None:
        raise RuntimeError(f"Could not locate Figure {number} image relationship")
    relationship_id = blip.get(qn("r:embed"))
    document.part.related_parts[relationship_id]._blob = image_path.read_bytes()

    with Image.open(image_path) as image:
        width_px, height_px = image.size
    cx = round(width_inches * 914400)
    cy = round(cx * height_px / width_px)
    for extent in drawing.iter(qn("wp:extent")):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
    for extent in drawing.iter(qn("a:ext")):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))


def paragraph_text(element):
    return "".join(node.text or "" for node in element.iter(qn("w:t"))).strip()


def has_page_break(element):
    return any(node.get(qn("w:type")) == "page" for node in element.iter(qn("w:br")))


def move_figure_2_after_table(document, anchor_element):
    children = list(document.element.body.iterchildren())
    caption_index = next(
        (
            index
            for index, element in enumerate(children)
            if element.tag == qn("w:p") and paragraph_text(element).startswith("Figure 2.")
        ),
        None,
    )
    if caption_index is None or caption_index < 2 or caption_index + 1 >= len(children):
        raise RuntimeError("Could not locate the complete Figure 2 block")

    pre_break = children[caption_index - 2]
    drawing = children[caption_index - 1]
    caption = children[caption_index]
    post_break = children[caption_index + 1]
    if not any(True for _ in drawing.iter(qn("w:drawing"))):
        raise RuntimeError("Expected the Figure 2 drawing immediately before its caption")
    if not has_page_break(pre_break) or not has_page_break(post_break):
        raise RuntimeError("Expected page breaks around Figure 2")

    anchor = anchor_element
    for element in (pre_break, drawing, caption, post_break):
        anchor.addnext(element)
        anchor = element


def add_synthesis_cross_reference(document):
    for paragraph in document.paragraphs:
        if not paragraph.text.startswith("The principal finding is"):
            continue
        for run in paragraph.runs:
            if "Figure 2 shows" in run.text:
                run.text = run.text.replace(
                    "Figure 2 shows",
                    "Table 1 summarizes these findings and their implications for reuse; Figure 2 shows",
                    1,
                )
                return
    raise RuntimeError("Could not add the Table 1 cross-reference to the Discussion")


def remove_blank_heading_before_supplement(document):
    paragraphs = document.paragraphs
    for index in range(len(paragraphs) - 2):
        blank_heading = paragraphs[index]
        page_break = paragraphs[index + 1]
        supplement_heading = paragraphs[index + 2]
        if (
            not blank_heading.text.strip()
            and blank_heading.style.name == "Heading 1"
            and has_page_break(page_break._p)
            and supplement_heading.text.startswith("Supplementary Ontology Files")
        ):
            blank_heading._element.getparent().remove(blank_heading._element)
            return


def main():
    document = Document(SOURCE)
    old_table = find_category_table(document)
    body_children = list(document.element.body.iterchildren())
    old_index = body_children.index(old_table._tbl)
    previous = body_children[old_index - 1]
    if previous.tag != qn("w:p"):
        raise RuntimeError("Expected a paragraph immediately before the category table")

    from docx.text.paragraph import Paragraph

    caption = Paragraph(previous, document._body)
    set_apa_number(caption, "Table 1")
    new_table = build_table(document)
    old_table._tbl.addnext(new_table._tbl)
    old_table._element.getparent().remove(old_table._element)
    table_title = insert_paragraph_before(new_table._tbl, document)
    set_apa_title(table_title, "Synthesis of Principal Empirical Findings and Implications for Reuse")
    table_note = insert_paragraph_after(new_table._tbl, document)
    set_apa_note(
        table_note,
        "Counts are based on 144 included classes. Percentages may not total 100 because of rounding. "
        "BFO = Basic Formal Ontology; OWL = Web Ontology Language.",
    )
    move_figure_2_after_table(document, table_note._p)
    format_figure_apa(
        document,
        1,
        "Ontology-Artifact Selection Flow",
        "An appearance is one class in one registry/source-ontology context; a class is a unique IRI after "
        "deduplication. Dependency-only appearances are analysed at their native provider rather than counted "
        "as independent disease models.",
    )
    replace_figure_image(document, 1, FIGURE_1)
    format_figure_apa(
        document,
        2,
        "Ontological Commitments and Evidence Quality Among Included Classes",
        "Panels show (A) continuant-versus-occurrent commitment, (B) grounding of pathologicality, "
        "(C) reality-versus-classification coding, and (D) definition, comment, and parentage quality. "
        "Bar-end labels give class counts and percentages. Numbers within the stacked bars are class counts; "
        "percentages for panel D use 144 as the denominator.",
    )
    add_synthesis_cross_reference(document)
    remove_blank_heading_before_supplement(document)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    shutil.copy2(OUTPUT, CANONICAL)
    print(OUTPUT)
    print(CANONICAL)


if __name__ == "__main__":
    main()
