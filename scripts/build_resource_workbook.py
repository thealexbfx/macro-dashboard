"""Build a labelled synthetic XLSX envelope for resource tests, never economic data."""

import json
import random
import string
import sys
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
MIN_COMPRESSED = 586099
MIN_EXPANDED = 3550099
MIN_SHEET = 2375828
MIN_STRINGS = 50756


def column(n):
    value = ""
    while n:
        n, r = divmod(n - 1, 26)
        value = chr(65 + r) + value
    return value


def build():
    rng = random.Random(20261028)
    strings, lookup = [], {}

    def shared(text):
        if text not in lookup:
            lookup[text] = len(strings)
            strings.append(text)
        return lookup[text]

    def text_cell(col, row, text):
        return f'<c r="{col}{row}" t="s"><v>{shared(text)}</v></c>'

    names = {3: "Crude oil, Brent", 64: "Iron ore, cfr spot", 65: "Copper"}
    rows = [
        '<row r="1">'
        + text_cell("A", 1, "SYNTHETIC RESOURCE FIXTURE - NOT ECONOMIC DATA")
        + "</row>"
    ]
    rows.append(
        '<row r="5">'
        + "".join(
            text_cell(column(c), 5, names.get(c, f"Unused synthetic column {c}"))
            for c in range(2, 73)
        )
        + "</row>"
    )
    rows.append(
        '<row r="6">'
        + "".join(
            text_cell(
                column(c),
                6,
                "($/bbl)" if c == 3 else "($/dmtu)" if c == 64 else "($/mt)",
            )
            for c in range(2, 73)
        )
        + "</row>"
    )
    for i in range(801):
        row = i + 7
        year, month = 1960 + i // 12, i % 12 + 1
        cells = [text_cell("A", row, f"{year}M{month:02d}")]
        for c in range(2, 73):
            if i == 61 and c == 3:
                cells.append(text_cell(column(c), row, "..."))
            else:
                value = 50 + c + rng.random() * 100
                cells.append(f'<c r="{column(c)}{row}"><v>{value:.14f}</v></c>')
        rows.append(f'<row r="{row}">' + "".join(cells) + "</row>")
    for _ in range(1200):
        shared(
            "SYNTHETIC " + "".join(rng.choice(string.ascii_letters) for _ in range(50))
        )
    sheet = (
        '<worksheet xmlns="'
        + NS
        + '"><sheetData>'
        + "".join(rows)
        + "</sheetData></worksheet>"
    ).encode()
    shared_xml = (
        '<sst xmlns="'
        + NS
        + '">'
        + "".join("<si><t>" + escape(x) + "</t></si>" for x in strings)
        + "</sst>"
    ).encode()
    padding = max(0, MIN_EXPANDED - len(sheet) - len(shared_xml)) + 4096
    sheet = sheet.replace(
        b"</worksheet>",
        b"<!-- SYNTHETIC PADDING " + b"x" * padding + b" --></worksheet>",
    )

    def pack():
        result = BytesIO()
        with ZipFile(result, "w", compression=ZIP_DEFLATED) as z:
            z.writestr(
                "xl/workbook.xml",
                '<workbook xmlns="'
                + NS
                + '" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Monthly Prices" r:id="rId2"/></sheets></workbook>',
            )
            z.writestr(
                "xl/_rels/workbook.xml.rels",
                '<Relationships><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>',
            )
            z.writestr("xl/sharedStrings.xml", shared_xml)
            z.writestr("xl/worksheets/sheet2.xml", sheet)
        return result.getvalue()

    data = pack()
    if len(data) < MIN_COMPRESSED:
        raise ValueError("Synthetic compressed envelope unexpectedly too small")
    assert (
        len(data) < 4 * 1024**2
        and len(sheet) >= MIN_SHEET
        and len(shared_xml) >= MIN_STRINGS
    )
    manifest = {
        "kind": "synthetic_resource_envelope_not_economic_data",
        "months": 801,
        "selected_series": 3,
        "all_columns": 72,
        "compressed_bytes": len(data),
        "monthly_sheet_bytes": len(sheet),
        "shared_strings_bytes": len(shared_xml),
        "minimum_captured_compressed": MIN_COMPRESSED,
        "minimum_captured_expanded": MIN_EXPANDED,
    }
    return data, manifest


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    data, metadata = build()
    target.write_bytes(data)
    target.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata))
