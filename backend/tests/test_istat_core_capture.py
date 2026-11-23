import pytest

from scripts.capture_istat_core_history import MESSAGE, capture


def response(*, area="IT", omit=""):
    observations = "".join(
        f'<Obs TIME_PERIOD="{year}-Q{quarter}" OBS_VALUE="400000"/>'
        for year in range(1996, 2027)
        for quarter in range(1, 5 if year < 2026 else 4)
        if f"{year}-Q{quarter}" != omit
    )
    ns = MESSAGE[1:-1]
    return (
        f'<m:StructureSpecificData xmlns:m="{ns}"><m:Header>'
        '<m:Sender id="ISTAT"/><m:Structure structureID="IT1_NAG_08_1_0"/>'
        '<m:Prepared>2026-11-23T05:12:45</m:Prepared></m:Header><m:DataSet>'
        f'<Series DATA_DOMAIN="NAG" REF_AREA="{area}" COUNTERPART_AREA="_Z" '
        'FREQ="Q" UNIT_MULT="6" INDICATOR="NGDP_R_CH_SA_EUR">'
        f'{observations}</Series></m:DataSet></m:StructureSpecificData>'
    ).encode()


def test_istat_gdp_capture_requires_complete_quarters_and_national_identity():
    assert capture("G7-IT-01", response())["valid_observations"] == 123
    with pytest.raises(ValueError, match="Incomplete"):
        capture("G7-IT-01", response(omit="2008-Q3"))
    with pytest.raises(ValueError, match="Incomplete"):
        capture("G7-IT-01", response(omit="2026-Q3"))
    with pytest.raises(ValueError, match="identity"):
        capture("G7-IT-01", response(area="EA"))


def test_istat_nic_links_earlier_bases_and_keeps_the_published_level():
    from io import BytesIO

    from openpyxl import Workbook

    from scripts.capture_istat_cpi_history import SEGMENTS, capture as capture_cpi

    workbook = Workbook()
    it = workbook.active
    it.title = "IT"
    en = workbook.create_sheet("EN")
    headings = [
        "splicing coefficient from base 1995 to base 2010",
        "splicing coefficient from base 2010 to base 2015",
        "splicing coefficient from base 2015 to base 2025",
    ]
    for column, value in enumerate(headings, 4):
        en.cell(16, column, value)
    for sheet, row in [(it, 16), (en, 17)]:
        for column, value in enumerate(("00", "Gen.", "Indice generale", 1.398, 1.075, 1.226), 1):
            sheet.cell(row, column, value)
    buffer = BytesIO()
    workbook.save(buffer)
    series = []
    for selector, (_base, first, last) in SEGMENTS.items():
        rows = "".join(
            f'<Obs TIME_PERIOD="{year}-{month:02}" OBS_VALUE="105.6"/>'
            for year in range(1996, 2027)
            for month in range(1, 13)
            if first <= f"{year}-{month:02}" <= (last or "2026-10")
        )
        series.append(f'<Series FREQ="M" REF_AREA="IT" DATA_TYPE="{selector}" MEASURE="4" ECOICOP_2="00">{rows}</Series>')
    ns = MESSAGE[1:-1]
    xml = (
        f'<m:StructureSpecificData xmlns:m="{ns}"><m:Header>'
        '<m:Sender id="ISTAT"/><m:Structure structureID="IT1_167_745_DF_DCSP_NIC1B2025_6_1_0"/>'
        f'</m:Header><m:DataSet>{"".join(series)}</m:DataSet></m:StructureSpecificData>'
    ).encode()
    receipt = capture_cpi(xml, buffer.getvalue())
    assert receipt["valid_observations"] == 370
    first = receipt["observations"][0]
    assert first["value"] == pytest.approx(105.6 / (1.398 * 1.075 * 1.226))
    assert first["publisher_value"] == "105.6"
    assert first["publisher_base_year"] == 1995
    assert receipt["observations"][-1]["value"] == 105.6
