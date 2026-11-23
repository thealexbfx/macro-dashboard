import csv
from io import StringIO
from zipfile import ZipFile

import pytest

from scripts.capture_destatis_cpi_history import IDENTITY, capture


def export(path, values):
    columns = [*IDENTITY, "time", "1_variable_attribute_code", "value_unit", "value", "value_q"]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, delimiter=";")
    writer.writeheader()
    for month, value in values:
        writer.writerow({
            **IDENTITY, "time": "1991", "1_variable_attribute_code": f"MONAT{month:02d}",
            "value_unit": "2020=100", "value": value, "value_q": "e" if value != "..." else "",
        })
    with ZipFile(path, "w") as archive:
        archive.writestr("61111-0002_de_flat.csv", buffer.getvalue())
    return path


def test_pending_period_stays_in_receipt_without_staging_as_observation(tmp_path):
    older = export(tmp_path / "older", [(1, "60,5"), (2, "60,8")])
    recent = export(tmp_path / "recent", [(2, "60,8"), (3, "...")])
    receipt = capture(older, recent)
    assert receipt["matched_overlap"] == 1
    assert [point["value"] for point in receipt["observations"]] == [60.5, 60.8]
    assert receipt["unpublished_periods"] == [
        {"period": "1991-03", "value": None, "publisher_flag": "..."},
    ]


@pytest.mark.parametrize("recent,error", [
    ([(2, "61,0"), (3, "61,2")], "overlapping periods"),
    ([(2, "60,8"), (4, "61,2")], "contiguous"),
])
def test_rejects_conflicting_or_incomplete_exports(tmp_path, recent, error):
    older = export(tmp_path / "older", [(1, "60,5"), (2, "60,8")])
    recent = export(tmp_path / "recent", recent)
    with pytest.raises(ValueError, match=error):
        capture(older, recent)
