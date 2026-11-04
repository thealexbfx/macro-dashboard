"""Presentation acceptance and reviewed screenshots over the permitted synthetic fixture."""
import json
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from test_research_journey_browser import finding_report
from test_research_foundation_browser import URL


def main():
    phase = int(os.environ.get('ML_REDESIGN_PHASE', '1'))
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
        page.get_by_label('New research question').fill('What is changing in this synthetic sample?')
        page.get_by_role('button',name='Start research',exact=True).click()
        expect(page.get_by_label('Investigation question')).to_have_value('What is changing in this synthetic sample?')
        page.get_by_label('Investigation notes').fill('Keep this across navigation.')
        nav.get_by_role('button',name='Home',exact=True).click()
        nav.get_by_role('button',name='Research',exact=True).click()
        expect(page.get_by_label('Investigation notes')).to_have_value('Keep this across navigation.')
        page.get_by_label('Help and availability').click()
        expect(page.get_by_text('AI is not active.',exact=False)).to_be_visible()
        page.get_by_label('Help and availability').click()
        assert not errors, errors
        print(json.dumps(dict(redesign_phase=phase,passed=True,primary_sections=4,home_markets=3,page_errors=errors)))
        browser.close()

if __name__=='__main__':
    main()
