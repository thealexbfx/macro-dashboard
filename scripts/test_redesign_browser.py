"""Presentation acceptance and reviewed screenshots over the permitted synthetic fixture."""
import json
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from test_research_journey_browser import finding_report
from test_research_foundation_browser import URL, writing


def main():
    phase = int(os.environ.get('ML_REDESIGN_PHASE', '4'))
    output = Path(os.environ.get('BATCH0_BROWSER_ARTIFACTS', '/tmp/batch0-browser'))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = dict(headless=True)
        if os.environ.get('BATCH0_CHROME'):
            options['executable_path'] = os.environ['BATCH0_CHROME']
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport=dict(width=1440, height=1000))
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        response=page.request.post(URL+'/api/v2/compare',data=dict(datasets=['fixture_catalog_002','fixture_catalog_016'],start='2000-01-01',end='2009-12-31',rolling_window=24))
        assert response.status==200
        report,question=finding_report(response.json())
        page.route('**/api/v2/discovery',lambda route:route.fulfill(json=report))
        seed=dict(id='redesign-resume',title=question,research_question=question,version=3,note='Synthetic saved research',collection='Macro outlook',**report['findings'][0]['configuration'])
        page.add_init_script('if(!localStorage.getItem("ml-research"))localStorage.setItem("ml-research",'+json.dumps(json.dumps([seed]))+');')
        page.goto(URL,wait_until='networkidle')
        nav=page.get_by_role('navigation',name='Primary navigation')
        assert nav.get_by_role('button').all_text_contents()==['Home','Discover','Research','My Research']
        expect(page.get_by_label('New research question')).to_be_visible()
        expect(page.get_by_role('heading',name='Market pulse')).to_be_visible()
        expect(page.get_by_role('heading',name='Pick up where you left off')).to_be_visible()
        assert page.locator('.ml-market-grid .market-widget').count()==3
        expect(page.get_by_text('Stored in this browser',exact=False).first).to_be_visible()
        page.screenshot(path=str(output/f'phase-{phase}-home-desktop.png'),full_page=True)
        page.set_viewport_size(dict(width=390,height=844))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        page.screenshot(path=str(output/f'phase-{phase}-home-mobile.png'),full_page=True)
        if phase>=2:
            page.set_viewport_size(dict(width=1440,height=1000))
            nav.get_by_role('button',name='Discover',exact=True).click()
            card=page.locator('.discovery-story').first
            expect(card.get_by_role('button',name='Investigate',exact=True)).to_be_visible()
            assert card.get_by_role('button').count()==1
            expect(card.get_by_text('Evidence & sources',exact=True)).to_be_visible()
            page.screenshot(path=str(output/f'phase-{phase}-discover-desktop.png'),full_page=True)
            page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            page.screenshot(path=str(output/f'phase-{phase}-discover-mobile.png'),full_page=True)
            page.get_by_role('button',name='Dataset Explorer',exact=True).click()
            expect(page.get_by_label('Search datasets')).to_be_visible()
            expect(page.get_by_label('Catalog frequency')).not_to_be_visible()
            page.get_by_label('Search datasets').fill('Synthetic')
            expect(page.locator('.dataset-result').first).to_be_visible(timeout=60000)
            page.get_by_text('Preview',exact=True).first.click()
            expect(page.locator('.ml-dataset-preview').first).to_be_visible()
            checkbox=page.locator('.dataset-result').first.get_by_role('checkbox')
            checkbox.check()
            assert checkbox.is_checked()
            page.screenshot(path=str(output/f'phase-{phase}-data-mobile.png'),full_page=True)
            page.set_viewport_size(dict(width=1440,height=1000))
            page.screenshot(path=str(output/f'phase-{phase}-data-desktop.png'),full_page=True)
            nav.get_by_role('button',name='Home',exact=True).click()
        page.get_by_label('New research question').fill('What is changing in this synthetic sample?')
        page.get_by_role('button',name='Start research',exact=True).click()
        expect(page.get_by_label('Investigation question')).to_have_value('What is changing in this synthetic sample?')
        if phase>=3:
            expect(page.get_by_role('button',name='Save as evidence',exact=True)).to_be_enabled(timeout=60000)
            expect(page.get_by_label('Visualization mode')).not_to_be_visible()
            expect(page.get_by_label('Add data to research')).to_be_visible()
            page.set_viewport_size(dict(width=1440,height=1000))
            page.screenshot(path=str(output/f'phase-{phase}-research-desktop.png'),full_page=True)
            page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            page.screenshot(path=str(output/f'phase-{phase}-research-mobile.png'),full_page=True)
            page.get_by_label('Add data to research').fill('Synthetic 002')
            option=page.get_by_role('option').first
            expect(option).to_be_visible()
            option.click()
            assert page.locator('.ml-selected-data>button').count()==3
            page.locator('.ml-selected-data>button').last.click()
            assert page.locator('.ml-selected-data>button').count()==2
        writing(page,'Investigation notes').fill('Keep this across navigation.')
        nav.get_by_role('button',name='Home',exact=True).click()
        nav.get_by_role('button',name='Research',exact=True).click()
        expect(writing(page,'Investigation notes')).to_have_value('Keep this across navigation.')
        if phase>=4:
            page.set_viewport_size(dict(width=1440,height=1000))
            page.get_by_label('My conclusion',exact=True).fill('A provisional view, retained with its evidence.')
            page.get_by_role('button',name='Save and return to My Research',exact=True).click()
            expect(page.locator('.ml-library-card').filter(has_text='What is changing in this synthetic sample?')).to_be_visible()
            page.reload(wait_until='networkidle')
            expect(page.get_by_role('heading',name='My Research',exact=True)).to_be_visible()
            assert page.locator('.ml-library-card').count()>=2
            assert page.locator('.ml-library-card').filter(has_text='What is changing in this synthetic sample?').count()==1
            page.get_by_label('Search saved research').fill('What is changing')
            assert page.locator('.ml-library-card').count()==1
            card=page.locator('.ml-library-card').first
            expect(card.get_by_text('A provisional view, retained with its evidence.',exact=True)).to_be_visible()
            card.locator('summary').click()
            with page.expect_download() as event:
                card.get_by_role('button',name='Export research',exact=True).click()
            download=event.value
            exported=json.loads(Path(download.path()).read_text())
            assert exported['research_question']=='What is changing in this synthetic sample?'
            assert exported['conclusion']=='A provisional view, retained with its evidence.'
            card.locator('summary').click()
            page.get_by_label('Search saved research').fill('')
            page.screenshot(path=str(output/'phase-4-library-desktop.png'),full_page=True)
            page.set_viewport_size(dict(width=390,height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            page.screenshot(path=str(output/'phase-4-library-mobile.png'),full_page=True)
            card=page.locator('.ml-library-card').filter(has_text='What is changing in this synthetic sample?')
            card.get_by_role('button',name='Continue research',exact=False).click()
            expect(page.get_by_label('My conclusion',exact=True)).to_have_value('A provisional view, retained with its evidence.')
            page.go_back(wait_until='networkidle')
            expect(page.get_by_role('heading',name='My Research',exact=True)).to_be_visible()
            nav.get_by_role('button',name='Research',exact=True).click()
        page.get_by_label('Help and availability').click()
        # Ask now offers bounded, source-grounded observation comparisons,
        # rather than the former inactive AI placeholder.
        expect(page.get_by_text('Research with observed data',exact=True)).to_be_visible()
        expect(page.get_by_role('button',name='Ask MacroLens',exact=True)).to_be_visible()
        page.get_by_label('Help and availability').click()
        assert not errors, errors
        print(json.dumps(dict(redesign_phase=phase,passed=True,primary_sections=4,home_markets=3,page_errors=errors)))
        browser.close()

if __name__=='__main__':
    main()
