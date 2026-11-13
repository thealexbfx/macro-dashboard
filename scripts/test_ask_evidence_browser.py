"""Ask MacroLens browser acceptance against a disposable synthetic backend only."""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

URL = os.environ.get("BATCH0_BROWSER_URL", "http://127.0.0.1:3039")


def main():
    output = Path(os.environ.get("BATCH0_BROWSER_ARTIFACTS", "/tmp/batch0-browser"))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("BATCH0_CHROME"):
            options["executable_path"] = os.environ["BATCH0_CHROME"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(URL + "/?view=ai", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Ask MacroLens")).to_be_visible(timeout=60000)
        chooser = page.get_by_label("Dataset", exact=True)
        expect(chooser.locator("option").nth(1)).to_be_attached(timeout=30000)
        chosen = chooser.locator("option").nth(1).get_attribute("value")
        assert chosen and chosen != ""
        # Check exact API output independently of the browser presentation.
        preview_response = page.request.get(
            URL + "/api/v2/observations/" + chosen + "?preview=true&limit=40"
        )
        assert preview_response.status == 200
        preview = preview_response.json()["dataset"]
        assert preview["id"] == chosen
        points = sorted(
            {(r["date"], r["value"]) for r in preview["observations"]
             if r["value"] is not None and isinstance(r["value"], (int, float))},
            reverse=True,
        )
        assert len(points) >= 2

        chooser.select_option(chosen)
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_role("heading", name=preview["name"], exact=True)).to_be_visible(timeout=30000)
        explanation = page.locator("main").inner_text()
        assert points[0][0] in explanation and points[1][0] in explanation
        assert "Change =" in explanation
        assert "cannot establish a cause" in explanation
        assert "Dataset " + chosen in explanation
        page.screenshot(path=str(output / "ask-evidence-desktop.png"), full_page=True)

        # Fail closed on unavailable responses; never silently present old evidence.
        page.route(
            "**/api/v2/observations/" + chosen + "?*",
            lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"detail": "Synthetic unavailable source"}),
            ),
        )
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_text("Evidence is unavailable for this dataset.", exact=False)).to_be_visible()
        expect(page.get_by_text("Change =", exact=False)).to_have_count(0)
        page.unroute("**/api/v2/observations/" + chosen + "?*")

        # Changing publisher metadata between catalog listing and retrieval must
        # not make an unreviewed market source available in Ask.
        mismatched = dict(preview)
        mismatched["source"] = "Yahoo Finance"
        page.route(
            "**/api/v2/observations/" + chosen + "?*",
            lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps({"dataset": mismatched}),
            ),
        )
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_text("Evidence is unavailable for this dataset.", exact=False)).to_be_visible()
        expect(page.get_by_text("Change =", exact=False)).to_have_count(0)
        page.unroute("**/api/v2/observations/" + chosen + "?*")

        search = page.get_by_role("searchbox", name="Search datasets")
        search.fill("CPIAUCSL")
        expect(chooser.locator('option[value="cpi"]')).to_be_attached()
        chooser.select_option("cpi")
        page.get_by_label("Calculation", exact=True).select_option("percent")
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_text("Relative change =", exact=False)).to_be_visible()
        search.fill("unemployment")
        expect(chooser.locator('option[value="unemployment"]')).to_be_attached()
        chooser.select_option("unemployment")
        expect(page.get_by_label("Calculation", exact=True)).to_have_value("difference")
        expect(page.get_by_role("option", name="Relative percentage change")).to_have_count(0)

        # An exact ID outside the initial catalog page can be found and used.
        outside = "fixture_catalog_250"
        search.fill("")
        expect(chooser.locator(f'option[value="{outside}"]')).to_have_count(0)
        page.get_by_role("searchbox", name="Search datasets").fill(outside)
        expect(chooser.locator(f'option[value="{outside}"]')).to_be_attached()
        chooser.select_option(outside)
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_text("Dataset " + outside, exact=False)).to_be_visible()

        assert not errors, errors
        print(json.dumps({
            "ask_browser_checks": 16, "passed": True,
            "selected_fixture_dataset": chosen, "screenshots": 1, "page_errors": errors,
        }))
        browser.close()


if __name__ == "__main__":
    main()
