"""Research foundation browser acceptance, synthetic backend only."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

URL = "http://127.0.0.1:3039"

def records(page, store):
    return page.evaluate("""store=>new Promise((resolve,reject)=>{const o=indexedDB.open('macrolens-research');o.onsuccess=()=>{const db=o.result;const tx=db.transaction(store);const q=tx.objectStore(store).getAll();q.onsuccess=()=>{resolve(q.result);db.close();};q.onerror=()=>reject(q.error);};o.onerror=()=>reject(o.error);})""", store)

def main():
    output = Path(os.environ.get("BATCH0_BROWSER_ARTIFACTS", "/tmp/batch0-browser"))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("BATCH0_CHROME"):
            options["executable_path"] = os.environ["BATCH0_CHROME"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors, hydration = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: hydration.append(m.text) if "hydration" in m.text.lower() or "#418" in m.text else None)
        # Capture server HTML just before UTC midnight, hydrate that same response after it.
        page.clock.install(time=datetime(2026, 11, 2, 23, 59, 59, tzinfo=timezone.utc))
        server = page.request.get(URL).text()
        assert 'Opening local research' in server
        assert 'November 2, 2026' not in server
        page.clock.set_fixed_time(datetime(2026, 11, 3, 0, 0, 1, tzinfo=timezone.utc))
        page.route(URL, lambda route: route.fulfill(status=200, content_type="text/html", body=server))
        page.goto(URL, wait_until="networkidle")
        page.unroute(URL)
        page.get_by_role("button", name="Investigate", exact=True).click()
        expect(page.get_by_label("Investigation question")).to_be_visible()
        page.get_by_label("Investigation question").fill("Does the relationship survive revisions?")
        page.get_by_label("Investigation notes", exact=True).fill("My interpretation; not numerical evidence")
        expect(page.get_by_text("Draft saved on this browser", exact=False)).to_be_visible()
        draft = records(page, 'drafts')[0]['record']
        assert draft['end'] == '2026-11-02'
        assert draft['created_at'].startswith('2026-11-03T00:00:01')
        first_id = draft['id']
        page.get_by_role('button', name='Dataset Explorer', exact=True).click()
        page.get_by_role('button', name='Investigate', exact=True).click()
        expect(page.get_by_label('Investigation question')).to_have_value(draft['research_question'])
        page.reload(wait_until='networkidle')
        expect(page.get_by_label('Investigation notes', exact=True)).to_have_value(draft['note'])
        expect(page.get_by_role('button', name='Save investigation', exact=False)).to_be_enabled(timeout=60000)
        page.get_by_role('button', name='Save investigation', exact=False).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        first = records(page, 'saved')[0]
        assert first['id'] == first_id and first['revision'] == 1
        assert first['original_calculation'] == first['saved_calculation']
        assert first['saved_calculation']['exact_replay']['available'] is False
        assert first['saved_calculation']['parameters']['end'] == draft['end']
        # Deliver a changed synthetic calculation, preserving the original saved receipt.
        def revised(route):
            response = route.fetch()
            body = response.json()
            if response.status == 200:
                body['provenance']['result_fingerprint'] = 'd' * 64
                body['provenance']['statistics'][0]['correlation'] = 0.123
                body['statistics'][0]['correlation'] = 0.123
            route.fulfill(response=response, json=body)
        page.route('**/api/v2/compare', revised)
        page.reload(wait_until='networkidle')
        expect(page.get_by_role('button', name='Save investigation', exact=False)).to_be_enabled(timeout=60000)
        page.get_by_text('Saved evidence and current calculation', exact=True).click()
        expect(page.get_by_text('Result dddddddddddd', exact=False)).to_be_visible()
        assert records(page,'saved')[0]['saved_calculation'] == first['saved_calculation']
        page.get_by_label('Investigation notes', exact=True).fill('Reconsidered after recalculation')
        page.get_by_role('button', name='Save investigation', exact=False).click()
        expect(page.get_by_text('Investigation saved on this browser', exact=False)).to_be_visible()
        second = records(page, 'saved')
        assert len(second) == 1 and second[0]['revision'] == 2
        assert second[0]['created_at'] == first['created_at']
        assert second[0]['original_calculation'] == first['original_calculation']
        assert second[0]['saved_calculation']['result_fingerprint'] == 'd' * 64
        page.get_by_role('button', name='My Research', exact=True).click()
        page.get_by_role('button', name='+ New investigation', exact=True).click()
        page.get_by_label('Investigation question').fill('A separate question')
        expect(page.get_by_text('Draft saved on this browser', exact=False)).to_be_visible()
        assert records(page,'drafts')[0]['record']['id'] != first_id
        assert records(page,'saved')[0]['note'] == 'Reconsidered after recalculation'
        # A failure of the commit is visible; the active edit stays in the workspace.
        page.evaluate("""()=>{const original=IDBObjectStore.prototype.put;window.restoreWrites=()=>IDBObjectStore.prototype.put=original;IDBObjectStore.prototype.put=function(){throw new DOMException('Synthetic quota exceeded','QuotaExceededError');};}""")
        page.get_by_label('Investigation notes', exact=True).fill('Keep this unsaved draft')
        expect(page.get_by_role('alert').filter(has_text='Synthetic quota exceeded')).to_be_visible()
        expect(page.get_by_label('Investigation notes', exact=True)).to_have_value('Keep this unsaved draft')
        page.evaluate('()=>{window.restoreWrites();}')
        page.get_by_role('button', name='Retry draft save').click()
        expect(page.get_by_text('Draft saved on this browser', exact=False)).to_be_visible()
        page.reload(wait_until='networkidle')
        expect(page.get_by_label('Investigation notes', exact=True)).to_have_value('Keep this unsaved draft')
        assert not errors and not hydration, (errors, hydration)
        page.screenshot(path=str(output/'research-foundation.png'), full_page=True)
        # Corrupt legacy data and an unavailable storage engine cannot crash the page.
        broken = browser.new_page()
        broken.add_init_script("localStorage.setItem('ml-research','broken-json');")
        broken.goto(URL, wait_until='networkidle')
        broken.get_by_role('button', name='Investigate', exact=True).click()
        expect(broken.get_by_role('alert').filter(has_text='original browser copy was retained')).to_be_visible()
        assert broken.evaluate("localStorage.getItem('ml-research')") == 'broken-json'
        unavailable = browser.new_page()
        unavailable.add_init_script("Object.defineProperty(window,'indexedDB',{value:undefined});")
        unavailable.goto(URL, wait_until='networkidle')
        # Navigation must not silently drop an unsaved in-memory draft.
        unavailable.get_by_role('button', name='Investigate', exact=True).click()
        # Storage errors are also displayed globally so recovery is accessible on Today.
        expect(unavailable.get_by_role('alert').filter(has_text='storage is unavailable')).to_be_visible()
        print(json.dumps({'research_foundation_checks': 16, 'passed': True, 'midnight': {'server_response_clock':'2026-11-02T23:59:59Z','hydration_clock':'2026-11-03T00:00:01Z','end':'2026-11-02','page_errors':errors,'hydration_errors':hydration}}))
        browser.close()

if __name__ == '__main__':
    main()
