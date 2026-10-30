"""Browser assertions against the disposable fixture, never a production URL."""

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    output = Path(os.environ.get("BATCH0_BROWSER_ARTIFACTS", "/tmp/batch0-browser"))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("BATCH0_CHROME"):
            options["executable_path"] = os.environ["BATCH0_CHROME"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        saved = [
            {
                "id": "old-native",
                "title": "Synthetic monthly comparison",
                "datasets": ["fixture_catalog_002", "fixture_catalog_016"],
                "version": 3,
                "note": "Preserve me",
                "collection": "Macro outlook",
                "start": "2000-01-01",
                "end": "2009-12-31",
                "timeframe": "Saved",
            },
            {
                "id": "retired",
                "title": "Retired research",
                "datasets": ["retired_id", "wb_copper_monthly"],
                "version": 3,
                "note": "Keep old references",
                "collection": "Macro outlook",
                "start": "2000-01-01",
                "end": "2009-12-31",
                "timeframe": "Saved",
            },
        ]
        page.add_init_script(
            "if(!localStorage.getItem('ml-research')){localStorage.setItem('ml-research',"
            + json.dumps(json.dumps(saved))
            + ");localStorage.setItem('ml-favorites','[\"retired_id\",\"fixture_catalog_002\"]');}"
        )
        page.goto("http://127.0.0.1:3039", wait_until="networkidle")
        page.get_by_role("button", name="Dataset Explorer", exact=True).click()
        expect(page.get_by_text("309 public datasets", exact=False)).to_be_visible(
            timeout=60000
        )
        page.get_by_role("button", name="Next page").click(timeout=60000)
        expect(page.get_by_text("Page 2", exact=False)).to_be_visible()
        page.get_by_label("Catalog frequency").select_option("annual")
        expect(page.get_by_text("Page 1", exact=False)).to_be_visible()
        page.get_by_label("Catalog region").select_option("JP")
        page.get_by_label("Catalog provider").select_option("fixture_ons")
        expect(page.get_by_role("row").nth(1)).to_contain_text("annual", timeout=30000)
        page.screenshot(path=str(output / "explorer-desktop.png"), full_page=True)
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(
            has_text="Synthetic monthly comparison"
        ).get_by_role("button", name="Open investigation").click()
        expect(page.locator(".workspace-chart").first).to_be_visible(timeout=30000)
        expect(
            page.get_by_text("110 overlapping observations", exact=False)
        ).to_be_visible(timeout=30000)
        page.screenshot(path=str(output / "investigate-desktop.png"), full_page=True)
        # Exercise discrete event rendering, including two observations at one instant.
        events = {
            "id": "event-browser",
            "title": "Synthetic event evidence",
            "datasets": ["fixture_catalog_005"],
            "version": 3,
            "note": "events",
            "collection": "Macro outlook",
            "start": "2000-01-01",
            "end": "2000-12-31",
            "timeframe": "Saved",
        }
        page.evaluate(
            "record=>localStorage.setItem('ml-research',JSON.stringify([...JSON.parse(localStorage.getItem('ml-research')),record]))",
            events,
        )
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(
            has_text="Synthetic event evidence"
        ).get_by_role("button", name="Open investigation").click()
        expect(page.locator(".recharts-scatter-symbol").first).to_be_visible(
            timeout=30000
        )
        page.screenshot(path=str(output / "investigate-events.png"), full_page=True)
        page.evaluate(
            "records=>localStorage.setItem('ml-research',JSON.stringify(records))",
            saved,
        )
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(has_text="Retired research").get_by_role(
            "button", name="Open investigation"
        ).click()
        expect(
            page.get_by_text(
                "Some saved dataset references are unavailable", exact=False
            )
        ).to_be_visible(timeout=30000)
        assert json.loads(page.evaluate("localStorage.getItem('ml-research')")) == saved
        assert "retired_id" in json.loads(
            page.evaluate("localStorage.getItem('ml-favorites')")
        )
        for path in (
            "catalog/wb_copper_monthly",
            "observations/wb_copper_monthly",
            "catalog/wb_iron_ore_monthly",
            "observations/wb_brent_monthly",
        ):
            assert (
                page.request.get("http://127.0.0.1:3039/api/v2/" + path).status == 404
            )
        page.get_by_role("button", name="Dataset Explorer", exact=True).click()
        page.route(
            "**/api/v2/catalog/search",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Synthetic failure"}',
            ),
        )
        page.get_by_label("Search datasets").fill("Synthetic")
        expect(
            page.get_by_role("alert").filter(has_text="Synthetic failure")
        ).to_contain_text("Synthetic failure", timeout=30000)
        page.unroute("**/api/v2/catalog/search")
        page.get_by_role("button", name="Retry catalog").click()
        expect(page.get_by_role("row").nth(1)).to_be_visible(timeout=30000)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(output / "explorer-mobile.png"), full_page=True)
        assert not errors, errors
        print(
            json.dumps(
                {
                    "browser_checks": 20,
                    "passed": True,
                    "screenshots": 4,
                    "page_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
