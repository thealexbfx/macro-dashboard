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
        # Admin UI uses a synthetic response; backend authentication/header
        # regressions run independently. Never provide a real token to this test.
        page.goto("http://127.0.0.1:3039/data-health", wait_until="networkidle")
        expect(
            page.get_by_role("heading", name="Data health", exact=True)
        ).to_be_visible()
        assert (
            page.request.get(
                "http://127.0.0.1:3039/api/v2/discovery/admin/data-health"
            ).status
            == 403
        )
        token = "synthetic-browser-health-token"

        def health_fixture(route):
            assert route.request.headers.get("authorization") == "Bearer " + token
            assert token not in route.request.url
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "as_of": "2026-11-02T12:00:00Z",
                        "summary": {
                            "public": 194,
                            "automatic_refresh": 194,
                            "verified_automatic_refresh": 193,
                            "healthy": 193,
                            "needs_attention": 1,
                        },
                        "items": [
                            {
                                "id": "fixture",
                                "name": "Synthetic source",
                                "provider": "fixture",
                                "frequency": "monthly",
                                "last_success": "2026-11-01T12:00:00Z",
                                "last_check": "2026-11-02T12:00:00Z",
                                "next_check": "2026-11-03T12:00:00Z",
                                "latest_observation_date": "2026-09-01",
                                "health": "source_failure",
                                "failures": 1,
                                "error_code": "http_503",
                            }
                        ],
                        "total": 1,
                        "next_offset": None,
                        "resources": {
                            "sqlite_bytes": {"database": 1024},
                            "free_disk_bytes": 500 * 1024**2,
                            "disk_attention": False,
                            "memory.current": "300000000",
                            "memory.max": "536870912",
                        },
                    }
                ),
            )

        page.route("**/api/v2/discovery/admin/data-health?*", health_fixture)
        page.get_by_label("Administrator token", exact=True).fill(token)
        page.get_by_role("button", name="Refresh report", exact=True).click()
        expect(page.get_by_text("Source check failed", exact=False)).to_be_visible()
        assert token not in page.evaluate("JSON.stringify(localStorage)")
        page.screenshot(path=str(output / "data-health-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(output / "data-health-desktop.png"), full_page=True)
        page.get_by_role("button", name="Lock report", exact=True).click()
        expect(page.get_by_label("Administrator token", exact=True)).to_have_value("")
        expect(page.get_by_text("Synthetic source", exact=True)).to_have_count(0)
        assert not errors, errors
        print(
            json.dumps(
                {
                    "browser_checks": 26,
                    "passed": True,
                    "screenshots": 6,
                    "page_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
