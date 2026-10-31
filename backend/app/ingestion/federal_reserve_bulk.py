"""Stream official DDP ZIP/XML. Never materialize the large XML document tree."""

import calendar
import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import date

from backend.app.ingestion.expansion_sources import definition
from backend.app.ingestion.native import Observation


def parse_selected(entry, body):
    release, series = entry["source"]["selector"].split("/")
    d = definition(entry)
    points, metadata, active = [], {}, False
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        files = archive.infolist()
        if len(files) > 24 or sum(f.file_size for f in files) > 96 * 1024 * 1024:
            raise ValueError("Federal Reserve ZIP exceeds bounded expansion")
        with archive.open(f"{release}_data.xml") as source:
            # Standard ElementTree does not resolve external entities; reject DTDs.
            prefix = source.read(2048)
            if b"<!DOCTYPE" in prefix or b"<!ENTITY" in prefix:
                raise ValueError("Unexpected XML document declarations")
        with archive.open(f"{release}_data.xml") as source:
            root = None
            for event, element in ET.iterparse(source, events=("start", "end")):
                tag = element.tag.split("}")[-1]
                if root is None:
                    root = element
                if event == "start" and tag == "Series":
                    active = element.get("SERIES_NAME") == series
                    if active:
                        if metadata:
                            raise ValueError("Duplicate Federal Reserve series")
                        metadata = dict(element.attrib)
                        expected = entry.get("expected_source_attributes", {})
                        if any(element.get(k) != v for k, v in expected.items()):
                            raise ValueError(
                                "Federal Reserve units/frequency/selection changed"
                            )
                if event == "end" and tag == "Obs":
                    if active:
                        label, value = (
                            element.get("TIME_PERIOD"),
                            element.get("OBS_VALUE"),
                        )
                        flags = (f"OBS_STATUS={element.get('OBS_STATUS', '')}",)
                        period = label
                        if d.frequency == "monthly":
                            day = date.fromisoformat(label)
                            if day.day != calendar.monthrange(day.year, day.month)[1]:
                                raise ValueError(
                                    "Expected DDP month-end reference label"
                                )
                            period = label[:7]
                        points.append(
                            Observation(
                                period,
                                label,
                                float(value)
                                if value not in (None, "", "ND", "NA")
                                else None,
                                flags,
                            )
                        )
                        if len(points) > 50000:
                            raise ValueError(
                                "Federal Reserve observation budget exceeded"
                            )
                    element.clear()
                elif event == "end" and tag == "Series":
                    active = False
                    element.clear()
                    root.clear()
    if not metadata or not points:
        raise ValueError("Federal Reserve source series not found")
    return (
        d,
        tuple(points),
        {
            "source": "Federal Reserve Board",
            "source_attributes": metadata,
            "source_definition_note": entry.get("definition_note", ""),
            "update_risk": "DDP retirement announced; verify bulk ZIP continuity before scheduled use",
        },
    )
