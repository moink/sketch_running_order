import os
import subprocess

import pandas as pd
from reportlab.lib.enums import TA_CENTER

from lp_running_order import optimize_running_order
from running_order import Sketch

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether
from xml.sax.saxutils import escape

SEQ_COL = 'Fixed sequence'
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1JPa_l8abQdKdGwhZ7Yp7F9Hfl-4TFpsbGJd5qg-1qPM"
    "/export?format=csv&gid=1098282962"
)
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "running_order.pdf")
IGNORE_COLS = {'Character count', 'Casted count', 'Still needed'}
NOT_NAME_COLS = IGNORE_COLS.union({SEQ_COL})

def main():
    sketches = read_sketches()
    ordered = optimize_running_order(sketches, [])
    create_running_order_pdf(sketches, ordered, OUTPUT_FILE)
    subprocess.Popen(["xdg-open", OUTPUT_FILE])


def read_sketches():
    full_input = pd.read_csv(CSV_URL, index_col=0)
    names = sorted(set(full_input.columns).difference(NOT_NAME_COLS))
    num_sketches = (
        full_input.index.isna().argmax()
        if full_input.index.isna().any()
        else len(full_input)
    )
    sketch_rows = full_input.iloc[:num_sketches]
    index_at_position = {
        int(sequence): idx
        for idx, sequence in zip(sketch_rows.index, sketch_rows[SEQ_COL])
        if pd.notna(sequence)
    }
    occupied = set(index_at_position.values())
    remaining = iter(idx for idx in sketch_rows.index if idx not in occupied)
    ordered_indices = [
        index_at_position[i] if i in index_at_position else next(remaining)
        for i in range(num_sketches)
    ]
    casting = sketch_rows.loc[ordered_indices, names]
    sketches = []
    for sketch_name, row in casting.iterrows():
        anchored = pd.notna(sketch_rows.loc[sketch_name, SEQ_COL])
        cast = frozenset(row.index[row.notna()])
        sketches.append(Sketch(title=sketch_name, cast=cast, anchored=anchored))
    return sketches

def create_running_order_pdf(sketches, ordered, filename="running_order.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Running Order",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SketchTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        spaceBefore=4 * mm,
        spaceAfter=1.5 * mm,
        textColor=colors.black,
        keepWithNext=True,
    )
    cast_style = ParagraphStyle(
        "SketchCast",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceAfter=3 * mm,
        textColor=colors.HexColor("#444444"),
    )
    header_style = ParagraphStyle(
        "RunningOrderHeader",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
        textColor=colors.black,
    )
    story = [Paragraph("Sketch Bomb 2026-10-30", header_style)]
    for order, sketch_num in enumerate(ordered, 1):
        sketch = sketches[sketch_num]
        title = f"{order}. {escape(str(sketch.title))}"
        cast = ", ".join(
            escape(str(name)) for name in sorted(sketch.cast)
        )
        story.append(KeepTogether([
            Paragraph(title, title_style),
            Paragraph(cast, cast_style),
        ]))
    doc.build(story)

if __name__ == "__main__":
    main()