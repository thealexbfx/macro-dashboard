"""Private original-source histories must reject drift and incomplete responses."""
import pytest

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.official_snapshots import safe_url
from scripts.capture_insee_core_history import SERIES, SOURCE, capture


def response(mapping, *, missing_period=False, wrong_area=False):
    selector, freq, unit_code, area, _unit, first, title = SERIES[mapping]
    period = first
    next_period = "1996-02" if freq == "M" else "1975-Q2"
    last_period = "1996-03" if freq == "M" else "1975-Q3"
    observations = (
        f'<Obs TIME_PERIOD="{period}" OBS_VALUE="10" OBS_STATUS="A" OBS_REV="1"/>'
        + ("" if missing_period else f'<Obs TIME_PERIOD="{next_period}" OBS_STATUS="M"/>')
        + f'<Obs TIME_PERIOD="{last_period}" OBS_VALUE="11" OBS_STATUS="A"/>'
    )
    return (
        '<message:StructureSpecificData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message">'
        '<message:DataSet>'
        f'<Series IDBANK="{selector}" FREQ="{freq}" UNIT_MEASURE="{unit_code}" '
        f'UNIT_MULT="0" REF_AREA="{"wrong" if wrong_area else area}" TITLE_EN="{title}" LAST_UPDATE="2026-11-10">'
        f'{observations}</Series></message:DataSet></message:StructureSpecificData>'
    ).encode()


@pytest.mark.parametrize("mapping", SERIES)
def test_capture_retains_null_periods_and_publisher_markers(mapping):
    summary, points = capture(mapping, response(mapping))
    assert summary["publisher_nulls"] == 1
    assert summary["valid_observations"] == 2
    assert summary["rights_status"] == "PENDING"
    assert summary["production_approval"] == "NOT_APPROVED"
    assert points[1]["value"] is None
    assert "OBS_REV=1" in points[0]["publisher_flag"]
    assert "OBS_STATUS=M" in points[1]["publisher_flag"]


@pytest.mark.parametrize("mapping", SERIES)
def test_capture_rejects_missing_periods_and_country_drift(mapping):
    with pytest.raises(ValueError, match="Missing INSEE reference period"):
        capture(mapping, response(mapping, missing_period=True))
    with pytest.raises(ValueError, match="identity"):
        capture(mapping, response(mapping, wrong_area=True))


def test_capture_rejects_duplicate_series_and_xml_entities():
    raw = response("G7-FR-07")
    with pytest.raises(ValueError, match="one INSEE series"):
        capture("G7-FR-07", raw.replace(b"</Series>", b"</Series><Series/>"))
    with pytest.raises(ValueError, match="XML declarations"):
        capture("G7-FR-07", b'<!DOCTYPE data [<!ENTITY example "value">]>' + raw)


def test_insee_downloads_only_allow_the_reviewed_exact_series():
    for selector, *_ in SERIES.values():
        assert safe_url(SOURCE + selector) == SOURCE + selector
    for url in (
        SOURCE + "011814632",
        SOURCE + "011814630?token=secret",
        SOURCE + "011814630?startPeriod=2000",
        SOURCE.replace("www.bdm.insee.fr", "www.bdm.insee.fr.example.org") + "011814630",
    ):
        with pytest.raises(ProviderError, match="unapproved_official_host"):
            safe_url(url)
