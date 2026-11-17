"""Exercise the G7 development preview through the MacroLens frontend."""
import os

from playwright.sync_api import expect, sync_playwright


def main():
    origin = os.environ.get("MACROLENS_G7_PREVIEW_URL", "http://127.0.0.1:3001")
    with sync_playwright() as playwright:
        chrome = os.getenv("BATCH0_CHROME")
        browser = playwright.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        page = browser.new_page()
        page.goto(origin + "/?view=research", wait_until="domcontentloaded")
        selection = page.get_by_role("region", name="Research datasets")
        remove = selection.get_by_role("button", name="Remove ", exact=False)
        expect(remove).to_have_count(2, timeout=30000)
        remove.first.click()
        expect(remove).to_have_count(1)
        remove.first.click()
        expect(remove).to_have_count(0)
        page.get_by_role("button", name="Dataset Explorer", exact=True).click()
        expect(page.get_by_role("note")).to_contain_text("Private development preview", timeout=30000)
        page.get_by_text("More filters", exact=True).click()
        page.get_by_label("Catalog category").select_option("G7 core")
        expect(page.get_by_text("19 preview datasets · Page 1")).to_be_visible()
        expect(page.get_by_role("heading", name="Canada CPI: All-items", exact=True)).to_be_visible()
        page.get_by_role("button", name="Next page").click()
        expect(page.get_by_text("19 preview datasets · Page 2")).to_be_visible()

        datasets = {"ca_cpi_all_items_nsa": "Canada CPI: All-items",
                    "g7_fr_07": "France headline CPI (INSEE)"}
        for key, name in datasets.items():
            page.get_by_label("Search datasets").fill(key)
            page.get_by_role("checkbox", name=f"Add {name} to research", exact=True).check()
        with page.expect_response(
            lambda response: response.url.endswith("/api/v2/compare")
            and response.request.method == "POST"
            and set(response.request.post_data_json["datasets"]) == set(datasets),
            timeout=30000,
        ) as calculation:
            page.get_by_role("button", name="Research with selected (2/4)").click()
        response = calculation.value
        assert response.ok, response.text()
        result = response.json()
        assert {series["id"] for series in result["series"] if series["observations"]} == set(datasets)
        assert len(result["provenance"]["datasets"]) == 2

        question = "How did headline CPI move in France and Canada?"
        page.get_by_label("Investigation question").fill(question)
        page.get_by_role("button", name="Save and return to My Research").click()
        card = page.get_by_role("article").filter(has_text=question)
        expect(card).to_be_visible(timeout=30000)
        page.reload(wait_until="domcontentloaded")
        card.get_by_role("button", name="Continue research").click(timeout=30000)
        expect(page.get_by_label("Investigation question")).to_have_value(question)
        for name in datasets.values():
            expect(page.get_by_role("region", name="Research datasets")).to_contain_text(name)

        page.goto(origin + "/?view=ai", wait_until="domcontentloaded")
        page.get_by_label("Search datasets", exact=True).fill("g7_fr_07")
        france = page.get_by_label("Dataset", exact=True)
        expect(france.locator('option[value="g7_fr_07"]')).to_have_count(1, timeout=30000)
        france.select_option("g7_fr_07")
        page.get_by_role("button", name="Show evidence").click()
        expect(page.get_by_text("Change =", exact=False)).to_be_visible(timeout=30000)
        expect(page.get_by_role("link", name="Source for France headline CPI (INSEE)")).to_have_attribute(
            "href", "https://www.bdm.insee.fr/series/sdmx/data/SERIES_BDM/011814630"
        )
        print("G7 filtering, CPI comparison, research save/reopen and Ask source evidence passed")
        browser.close()


if __name__ == "__main__":
    main()
