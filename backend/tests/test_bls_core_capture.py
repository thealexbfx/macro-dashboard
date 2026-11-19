"""BLS development histories preserve publisher gaps and reject incomplete proofs."""
import copy
import json

import pytest

from scripts.capture_bls_core_history import SERIES, metadata_row, parse_history


def fixture():
    metadata = {}
    series = []
    for mapping, spec in SERIES.items():
        meta = dict(spec['fields'], series_id=spec['id'], end_year='2026', end_period='M10')
        metadata[mapping] = metadata_row(('\t'.join(meta) + '\n' + '\t'.join(meta.values()) + '\n').encode(), spec)
        rows = []
        for year in range(int(meta['begin_year']), 2027):
            for month in range(1, 13 if year < 2026 else 11):
                rows.append(dict(year=str(year), period=f'M{month:02}', value='5', footnotes=[]))
        rows[-2].update(value='-', footnotes=[dict(code='X', text='Publisher unavailable')])
        rows.append(dict(year='2026', period='M13', value='5'))
        series.append(dict(seriesID=spec['id'], data=rows))
    windows = [dict(start=1913 + i * 10, end=min(2026, 1922 + i * 10), source_hash='a' * 64, bytes=100) for i in range(12)]
    return dict(status='REQUEST_SUCCEEDED', Results=dict(series=series), source_windows=windows), metadata


def test_continuous_history_retains_publisher_null_and_excludes_annual_average():
    payload, metadata = fixture()
    result = parse_history(json.dumps(payload).encode(), metadata)
    for mapping, row in result.items():
        assert row['first'] == metadata[mapping]['begin_year'] + '-01'
        assert row['last'] == '2026-10'
        assert row['publisher_nulls'] == 1
        assert row['observations'][-2]['value'] is None
        assert row['observations'][-2]['publisher_flag'] == 'X'
        assert row['excluded_annual_averages'] == 1
        assert row['production_approval'] == 'NOT_APPROVED'
        assert row['rights_status'] == 'PENDING'


@pytest.mark.parametrize('mutation', ['gap', 'duplicate', 'window', 'nonfinite', 'domain', 'unknown_null'])
def test_rejects_incomplete_or_invalid_source(mutation):
    payload, metadata = fixture()
    rows = payload['Results']['series'][0]['data']
    if mutation == 'gap':
        rows.pop(0)
    elif mutation == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == 'window':
        payload['source_windows'][0]['start'] = 1914
    else:
        rows[0]['value'] = {'nonfinite': 'NaN', 'domain': '-1', 'unknown_null': '..'}[mutation]
    with pytest.raises(ValueError):
        parse_history(json.dumps(payload).encode(), metadata)


def test_metadata_definition_drift_is_rejected():
    spec = SERIES['G7-US-07']
    meta = dict(spec['fields'], series_id=spec['id'], end_year='2026', end_period='M10')
    meta['seasonal'] = 'S'
    with pytest.raises(ValueError, match='definition'):
        metadata_row(('\t'.join(meta) + '\n' + '\t'.join(meta.values()) + '\n').encode(), spec)


def test_metadata_host_only_allows_reviewed_static_files():
    from backend.app.ingestion.contracts import ProviderError
    from backend.app.ingestion.official_snapshots import safe_url
    for spec in SERIES.values():
        assert safe_url(spec['metadata_url']) == spec['metadata_url']
    for url in ('https://download.bls.gov/other',
                SERIES['G7-US-07']['metadata_url'] + '?other=1'):
        with pytest.raises(ProviderError):
            safe_url(url)
