"""Full Research Journey acceptance against permitted disposable data, no production."""
import copy
import hashlib
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from test_research_foundation_browser import records, URL


def revised_calculation(body):
    """Revise one synthetic level observation and recalculate paired/rolling results."""
    first = body['series'][0]
    last = next(o for o in reversed(first['observations']) if o['value'] is not None)
    last['value'] += 12
    raw = body['raw_observations'][first['id']]
    next(o for o in raw if o['date'] == last['date'])['value'] += 12
    for s in body['statistics']:
        left = {o['date']: o['value'] for o in body['series'][0]['observations']}
        right = {o['date']: o['value'] for o in body['series'][1]['observations']}
        dates = sorted(d for d in left if left[d] is not None and right.get(d) is not None)
        s['correlation'] = statistics.correlation([left[d] for d in dates], [right[d] for d in dates])
        window = s['rolling_window']
        for point in s['rolling']:
            paired = [d for d in dates if d <= point['date']][-window:]
            point['value'] = statistics.correlation([left[d] for d in paired], [right[d] for d in paired]) if len(paired) == window else None
    for point in body.get('scatter', []):
        if point['date'] == last['date']:
            point['x'] = last['value']
    fingerprint = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    receipt = body['provenance']
    receipt['calculated_at'] = datetime.now(timezone.utc).isoformat()
    receipt['datasets'][0]['input_fingerprint'] = fingerprint(raw)
    receipt['statistics'] = [{k: v for k, v in s.items() if k != 'rolling'} for s in body['statistics']]
    receipt['result_fingerprint'] = fingerprint({k: body[k] for k in ['series', 'statistics', 'alignment']})
    return body


def finding_report(calculation):
    workspace = dict(mode='separate', chart_type='line', layout='stacked', axes='shared', axis_assignment={}, recession=False, lead_lag=dict(dataset_id='', periods=0, unit='months'), hidden=[])
    config = dict(datasets=['fixture_catalog_002', 'fixture_catalog_016'], start='2000-01-01', end='2009-12-31', transformations={id: 'level' for id in ['fixture_catalog_002', 'fixture_catalog_016']}, horizons={}, observation_basis='native', timeframe='Custom', alignment='native', rolling_window=24, workspace=workspace)
    question = 'Does this synthetic relationship depend on the period?'
    points = calculation['series'][0]['observations']
    usable = sum(o['value'] is not None for o in points)
    expected = len(points)
    finding = dict(id='journey-fixture', type='correlation', classification='descriptive', label='Synthetic relationship', headline='A synthetic relationship worth investigating', datasets=config['datasets'], observation_date='2009-12-01', frequency='monthly', rationale='Offline acceptance fixture only', evidence=dict(observation_date='2009-12-01', baseline=dict(start='2000-01-01', end='2009-12-31', observations=usable, expected=expected, missing=expected-usable, completeness=usable/expected), recent_correlation=calculation['statistics'][0]['correlation'], baseline_correlation=calculation['statistics'][0]['correlation'], method='Synthetic fixture full-period comparison; not a live discovery scan'), ranking=dict(score=50, components={}, meaning='Synthetic fixture, not a current signal'), configuration=config, preview=[dict(id=s['id'], name=s['name'], units=s['units'], observations=s['observations'][-24:]) for s in calculation['series']], sources=[], limitations=['Synthetic data cannot support a real economic conclusion.'], methodology_version='fixture-1', suggestions=[dict(id='q1', label=question, origin='Synthetic finding', context='Compare periods', configuration=config)])
    return dict(findings=[finding], generated_at='2026-11-01T12:00:00Z', as_of='2009-12-01', snapshot_fingerprint='fixture-original', universe=dict(single_series=2, curated_pairs=1, exploratory_pairs=0, pairs=[], transformations={}), qualified_before_deduplication=1, excluded=[], methodology={}, limitations=['Synthetic acceptance only'], methodology_version='fixture-1'), question


def main():
    output = Path(os.environ.get('BATCH0_BROWSER_ARTIFACTS', '/tmp/batch0-browser'))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        manual = '--manual' in sys.argv
        options = dict(headless=not manual)
        if os.environ.get('BATCH0_CHROME'):
            options['executable_path'] = os.environ['BATCH0_CHROME']
        browser = p.chromium.launch(**options)
        context = browser.new_context(viewport=dict(width=1440, height=1000))
        page = context.new_page()
        errors = []
        context.on('weberror', lambda error: errors.append(str(error.error)))
        response = page.request.post(URL + '/api/v2/compare', data=dict(datasets=['fixture_catalog_002', 'fixture_catalog_016'], start='2000-01-01', end='2009-12-31', rolling_window=24))
        assert response.status == 200, response.text()
        report, question = finding_report(response.json())
        context.route('**/api/v2/discovery', lambda route: route.fulfill(json=report))
        page.goto(URL, wait_until='networkidle')
        if manual:
            page.get_by_role('navigation').get_by_role('button', name='Discover', exact=True).click()
            print('Manual synthetic Research Journey preview. Close the browser window to finish.', flush=True)
            page.wait_for_event('close', timeout=0)
            browser.close()
            return
        page.get_by_role('button', name='Discover', exact=True).click()
        card = page.locator('.discovery-story').filter(has_text=report['findings'][0]['headline'])
        card.get_by_role('button', name='Investigate', exact=True).click()
        expect(page.get_by_label('Investigation question')).to_have_value(question)
        expect(page.get_by_label('Working hypothesis')).to_be_visible()
        expect(page.get_by_role('button', name='Attach supporting calculation', exact=True)).to_be_enabled(timeout=60000)
        draft = records(page, 'drafts')
        assert draft[-1]['record']['datasets'] == report['findings'][0]['datasets'] or any(d['record']['datasets'] == report['findings'][0]['datasets'] for d in draft)
        page.get_by_label('Working hypothesis').fill('A shared trend might explain the relationship.')
        page.get_by_role('button', name='Attach supporting calculation', exact=True).click()
        page.get_by_label('Annotation for evidence 1').fill('Descriptive support; causality is not established.')
        page.get_by_role('button', name='Attach supporting calculation', exact=True).click()
        expect(page.get_by_role('alert').filter(has_text='already attached')).to_be_visible()
        expect(page.get_by_label('Evidence 2', exact=True)).to_have_count(0)
        # Change the analytical display and attach a genuinely distinct calculation.
        page.get_by_text('Individual series displays', exact=False).click()
        page.get_by_label('Transformation for fixture_catalog_002').select_option('percent')
        expect(page.get_by_role('button', name='Attach contradictory calculation', exact=True)).to_be_enabled(timeout=60000)
        page.get_by_role('button', name='Attach contradictory calculation', exact=True).click()
        expect(page.get_by_label('Evidence 2', exact=True)).to_be_visible()
        page.get_by_label('Annotation for evidence 2').fill('Different transformations change the comparison.')
        page.get_by_label('Alternative explanations', exact=True).fill('A common trend or the selected sample may explain this.')
        page.get_by_label('Limitations and uncertainty', exact=True).fill('Synthetic sample; revised observations; no causal identification.')
        conclusion = 'Provisional: investigate changes before interpreting the levels.'
        page.get_by_label('Provisional conclusion').fill(conclusion)
        page.get_by_label('Investigation notes').fill('Keep my working notes.')
        page.get_by_role('button', name='Dataset Explorer', exact=True).click()
        page.get_by_role('button', name='Discover', exact=True).click()
        page.get_by_role('navigation').get_by_role('button', name='Research', exact=True).click()
        expect(page.get_by_label('Provisional conclusion')).to_have_value(conclusion)
        expect(page.get_by_role('button', name='Attach supporting calculation', exact=True)).to_be_enabled(timeout=60000)
        page.get_by_role('button', name='Save and return to My Research', exact=True).click()
        expect(page.locator('.research-grid').get_by_role('heading', name=question, exact=True)).to_be_visible()
        saved = next(r for r in records(page, 'saved') if r['research_question'] == question)
        identity = saved['id']
        original = copy.deepcopy(saved)
        assert saved['revision'] == 1 and len(saved['supporting_evidence']) == len(saved['contradictory_evidence']) == 1
        assert saved['workspace']['chart_type'] == 'line' and saved['rolling_window'] == 24
        assert saved['discovery']['finding'] == report['findings'][0]
        assert saved['supporting_evidence'][0]['capture']['receipt']['result_fingerprint'] != saved['contradictory_evidence'][0]['capture']['receipt']['result_fingerprint']
        page.reload(wait_until='networkidle')
        page.get_by_role('button', name='My Research', exact=True).click()
        page.locator('.research-grid').get_by_role('button', name='Open investigation', exact=False).click()
        expect(page.get_by_label('Working hypothesis')).to_have_value(saved['working_hypothesis'])
        question2 = question + ' What survives a revision?'
        conclusion2 = 'Still provisional; the attached evidence needs a robustness check.'
        page.get_by_label('Investigation question').fill(question2)
        page.get_by_label('Provisional conclusion').fill(conclusion2)
        page.get_by_role('button', name='Save research', exact=True).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        assert len(records(page, 'saved')) == 1
        assert records(page, 'saved')[0]['id'] == identity and records(page, 'saved')[0]['revision'] == 2
        # Use captured settings with latest data, not historical replay.
        page.get_by_role('button', name='Use saved settings with latest data', exact=True).first.click()
        expect(page.get_by_label('Transformation for fixture_catalog_002')).to_have_value('level')
        expect(page.get_by_text('Draft saved on this browser', exact=False)).to_be_visible()
        def revised(route):
            response = route.fetch()
            body = response.json()
            if response.status == 200:
                body = revised_calculation(body)
            route.fulfill(response=response, json=body)
        page.route('**/api/v2/compare', revised)
        page.reload(wait_until='networkidle')
        expect(page.get_by_text('Current calculation differs from this attachment.', exact=False).first).to_be_visible(timeout=60000)
        expect(page.get_by_label('Provisional conclusion')).to_have_value(conclusion2)
        before = records(page, 'saved')[0]
        assert before['supporting_evidence'] == original['supporting_evidence']
        assert before['contradictory_evidence'] == original['contradictory_evidence']
        page.get_by_role('button', name='Save research', exact=True).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        after = records(page, 'saved')[0]
        assert after['revision'] == 3 and after['conclusion'] == conclusion2
        assert after['original_calculation'] == original['original_calculation']
        assert after['discovery'] == original['discovery'] and after['supporting_evidence'] == original['supporting_evidence']
        expect(page.get_by_role('button', name='Attach supporting calculation', exact=True)).to_be_enabled(timeout=60000)
        page.locator('.research-workspace').scroll_into_view_if_needed()
        page.locator('.coverage-list').scroll_into_view_if_needed()
        page.screenshot(path=str(output/'research-journey-desktop.png'), full_page=True)
        # Revoked references fail through the existing catalog/compare boundary.
        page.unroute('**/api/v2/compare')
        context.route('**/api/v2/catalog/fixture_catalog_002', lambda route: route.fulfill(status=404, json=dict(detail='Unknown dataset')))
        context.route('**/api/v2/compare', lambda route: route.fulfill(status=422, json=dict(detail='Unknown dataset: fixture_catalog_002 (synthetic revoked reference)')))
        page.reload(wait_until='networkidle')
        expect(page.get_by_text('Some saved dataset references are unavailable', exact=False)).to_be_visible(timeout=60000)
        expect(page.get_by_role('button', name='Attach supporting calculation', exact=True)).to_be_disabled()
        page.get_by_label('Provisional conclusion').fill('Retained with a revoked reference; do not infer a new result.')
        page.get_by_label('Start date').fill('2001-01-01')
        page.get_by_role('button', name='Save research', exact=True).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        unavailable = records(page, 'saved')[0]
        assert unavailable['revision'] == 4 and unavailable['saved_calculation'] == after['saved_calculation']
        assert unavailable['supporting_evidence'] == original['supporting_evidence']
        # Real shared browser storage: stale edits in another tab must not overwrite.
        other = context.new_page()
        other.goto(URL, wait_until='networkidle')
        expect(other.get_by_label('Working hypothesis')).to_have_value(unavailable['working_hypothesis'])
        page.get_by_label('Working hypothesis').fill('First tab preserves this newer work.')
        expect(page.get_by_text('Draft saved on this browser', exact=False)).to_be_visible()
        other.get_by_label('Working hypothesis').fill('Stale second tab edits stay in memory.')
        expect(other.get_by_role('alert').filter(has_text='changed in another tab')).to_be_visible()
        other.get_by_role('button', name='Save research', exact=True).click()
        expect(other.get_by_role('alert').filter(has_text='changed in another tab')).to_be_visible()
        page.get_by_role('button', name='Save research', exact=True).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        assert records(page, 'saved')[0]['working_hypothesis'] == 'First tab preserves this newer work.'
        assert records(page, 'saved')[0]['revision'] == 5
        expect(other.get_by_label('Working hypothesis')).to_have_value('Stale second tab edits stay in memory.')
        # Mobile navigation, own question and separate-ID blank/provisional save.
        page.set_viewport_size(dict(width=390, height=844))
        page.get_by_role('button', name='My Research', exact=True).click()
        page.get_by_role('button', name='+ New investigation', exact=True).click()
        page.get_by_label('Investigation question').fill('My separate mobile question')
        page.get_by_label('Provisional conclusion').fill('No conclusion yet.')
        page.get_by_role('button', name='Save and return to My Research', exact=True).click()
        expect(page.locator('.research-grid').get_by_role('heading', name='My separate mobile question', exact=True)).to_be_visible()
        assert len(records(page, 'saved')) == 2 and len({r['id'] for r in records(page,'saved')}) == 2
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
        page.screenshot(path=str(output/'research-journey-mobile.png'), full_page=True)
        assert not errors, errors
        print(json.dumps(dict(research_journey_checks=15, passed=True, same_id=identity, saved_revision=5, revised_evidence_preserved=True, multi_tab_conflict_preserved=True, page_errors=errors)))
        browser.close()

if __name__ == '__main__':
    main()
