"""Exercise the G7 development preview through the MacroLens frontend."""
import os

from playwright.sync_api import expect, sync_playwright


def main():
    origin = os.environ.get("MACROLENS_G7_PREVIEW_URL", "http://127.0.0.1:3001")
    with sync_playwright() as playwright:
        chrome = os.getenv("BATCH0_CHROME")
        browser = playwright.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        page = browser.new_page()
        page.goto(origin + "/?view=data", wait_until="domcontentloaded")
        expect(page.get_by_role("note")).to_contain_text("Private development preview", timeout=30000)
        page.get_by_text("More filters", exact=True).click()
        page.get_by_label("Catalog category").select_option("G7 core")
        expect(page.get_by_text("17 preview datasets · Page 1")).to_be_visible()
        expect(page.get_by_role("heading", name="Canada CPI: All-items", exact=True)).to_be_visible()
        page.get_by_role("button", name="Next page").click()
        expect(page.get_by_text("17 preview datasets · Page 2")).to_be_visible()

        page.get_by_label("Search datasets").fill("g7_de_23")
        germany = page.get_by_role("checkbox", name="Add Germany 10-year government convergence yield to research")
        germany.check()
        page.get_by_label("Search datasets").fill("g7_fr_23")
        france = page.get_by_role("checkbox", name="Add France 10-year government convergence yield to research")
        france.check()
        page.get_by_role("button", name="Research with selected (2/4)").click()
        expect(page.get_by_role("heading", name="Research question", exact=True)).to_be_visible()
        print("G7 preview filter, pagination, search, and Investigate handoff passed")
        browser.close()


if __name__ == "__main__":
    main()
