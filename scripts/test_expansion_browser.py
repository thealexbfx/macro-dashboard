"""Real captured government histories in a loopback-only disposable preview."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    output = Path(
        os.environ.get("EXPANSION_BROWSER_ARTIFACTS", "/tmp/expansion-browser")
    )
    output.mkdir(parents=True, exist_ok=True)
    origin = os.environ.get("EXPANSION_BROWSER_ORIGIN", "http://127.0.0.1:3040").rstrip(
        "/"
    )
    parsed = urlsplit(origin)
    local = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    live = (
        origin == "https://www.macrolensresearch.com"
        and os.environ.get("EXPANSION_BROWSER_LIVE_APPROVED") == "1"
    )
    if not (local or live) or parsed.path or parsed.query or parsed.fragment:
        raise ValueError(
            "Loopback or explicitly approved exact production origin required"
        )
    target_id = os.environ.get("EXPANSION_BROWSER_DATASET", "eia_wti_spot_daily")
    target_name = os.environ.get("EXPANSION_BROWSER_NAME", "WTI crude oil spot")
    target_title = "Actual-source saved investigation"
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
                "title": target_title,
                "datasets": [target_id],
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
        full_catalog = json.loads(
            (
                Path(__file__).resolve().parents[1] / "catalog/release_candidates.json"
            ).read_text(encoding="utf-8")
        )
        total = int(
            os.environ.get(
                "EXPANSION_BROWSER_EXPECTED_PUBLIC",
                str(30 + len(full_catalog["datasets"])),
            )
        )
        expect(page.get_by_text(f"{total} public datasets", exact=False)).to_be_visible(
            timeout=60000
        )
        page.get_by_label("Search datasets").fill(target_name)
        expect(page.locator(".dataset-result").first).to_contain_text(
            target_name, timeout=30000
        )
        page.screenshot(path=str(output / "real-explorer.png"), full_page=True)
        page.get_by_role("button", name="My Research", exact=True).click()
        page.get_by_role("article").filter(has_text=target_title).get_by_role(
            "button", name="Continue research"
        ).click()
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
        ).get_by_role("button", name="Continue research").click()
        expect(
            page.get_by_text(
                "Some saved data is unavailable", exact=False
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
