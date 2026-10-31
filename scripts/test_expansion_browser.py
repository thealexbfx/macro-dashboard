"""Real captured government histories in a loopback-only disposable preview."""

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    output = Path(
        os.environ.get("EXPANSION_BROWSER_ARTIFACTS", "/tmp/expansion-browser")
    )
    output.mkdir(parents=True, exist_ok=True)
    origin = "http://127.0.0.1:3040"
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
                "id": "real-wti",
                "title": "WTI spot — actual EIA history",
                "datasets": ["eia_wti_spot_daily"],
                "version": 3,
                "note": "Keep actual source returns",
                "collection": "Macro outlook",
                "start": "2019-01-01",
                "end": "2021-12-31",
                "timeframe": "Saved",
            },
            {
                "id": "old-private",
                "title": "Preserved unavailable research",
                "datasets": ["wb_copper_monthly", "retired_id"],
                "version": 3,
                "note": "Keep old references",
                "collection": "Macro outlook",
                "start": "2000-01-01",
                "end": "2020-12-31",
                "timeframe": "Saved",
            },
        ]
        page.add_init_script(
            'localStorage.setItem("ml-research",'
            + json.dumps(json.dumps(saved))
            + ');localStorage.setItem("ml-favorites",JSON.stringify(["gold","retired_id"]));'
        )
        page.goto(origin, wait_until="networkidle")
        page.get_by_role("button", name="Dataset Explorer", exact=True).click()
        total = int(os.environ.get("EXPANSION_BROWSER_EXPECTED_PUBLIC", "198"))
        expect(page.get_by_text(f"{total} public datasets", exact=False)).to_be_visible(
            timeout=60000
        )
        page.get_by_label("Search datasets").fill("WTI crude oil spot")
        expect(page.get_by_role("row").nth(1)).to_contain_text("Cushing", timeout=30000)
        page.screenshot(path=str(output / "real-explorer.png"), full_page=True)
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(
            has_text="WTI spot — actual EIA history"
        ).get_by_role("button", name="Open investigation").click()
        expect(page.locator(".workspace-chart").first).to_be_visible(timeout=30000)
        page.screenshot(path=str(output / "real-wti-investigate.png"), full_page=True)
        for key in ["wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"]:
            assert page.request.get(origin + "/api/v2/catalog/" + key).status == 404
            assert (
                page.request.get(origin + "/api/v2/observations/" + key).status == 404
            )
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(
            has_text="Preserved unavailable research"
        ).get_by_role("button", name="Open investigation").click()
        expect(
            page.get_by_text(
                "Some saved dataset references are unavailable", exact=False
            )
        ).to_be_visible(timeout=30000)
        assert json.loads(page.evaluate('localStorage.getItem("ml-research")')) == saved
        assert "retired_id" in json.loads(
            page.evaluate('localStorage.getItem("ml-favorites")')
        )
        page.get_by_role("button", name="Dataset Explorer", exact=True).click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(output / "real-explorer-mobile.png"), full_page=True)
        assert not errors, errors
        (output / "results.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "private_direct_requests_denied": 6,
                    "saved_records_preserved": True,
                    "page_errors": errors,
                    "screenshots": 3,
                }
            ),
            encoding="utf-8",
        )
        browser.close()


if __name__ == "__main__":
    main()
