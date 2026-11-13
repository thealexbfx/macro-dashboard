"""Fail-closed checks for original Federal Reserve DDP archive changes."""
import io
import zipfile

import pytest

from backend.app.ingestion.federal_reserve_bulk import parse_selected


ENTRY = {
    "id": "fred_f007c60ecacde1bf5fb2",
    "name": "Federal Funds Effective Rate",
    "kind": "series",
    "region": "US",
    "units": "Percent",
    "frequency": "daily",
    "seasonal_adjustment": "Not Seasonally Adjusted",
    "source": {"provider": "federal_reserve", "selector": "H15/RIFSPFF_N.D"},
}


def archive(name, data):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as zipout:
        zipout.writestr(name, data)
    return stream.getvalue()


def test_html_or_nonzip_is_never_parsed_as_federal_reserve_history():
    with pytest.raises(ValueError, match="not a ZIP archive"):
        parse_selected(ENTRY, b"<html>maintenance</html>")


def test_changed_zip_member_does_not_get_inferred_as_original_series():
    with pytest.raises(ValueError, match="missing exact H15_data.xml"):
        parse_selected(ENTRY, archive("README.txt", b"not an observation file"))


def test_unexpected_xml_declarations_are_rejected():
    payload = b"<!DOCTYPE foo [<!ENTITY secret SYSTEM 'file:///etc/passwd'>]><foo/>"
    with pytest.raises(ValueError, match="Unexpected XML document declarations"):
        parse_selected(ENTRY, archive("H15_data.xml", payload))
