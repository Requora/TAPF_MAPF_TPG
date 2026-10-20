"""Browser QA for the served dashboard; requires the optional Playwright tool."""
import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(sys.argv[1])
    assert response.status == 200
    for language in ("zh-CN", "en"):
        assert page.locator("html").get_attribute("lang") == language
        page.locator('[data-view="flow"]').click()
        assert page.locator(".node").count() == 14
        assert page.locator(".edge.future").count() == 15
        for node_id in page.locator(".node").evaluate_all("nodes => nodes.map(n => n.dataset.id)"):
            page.locator(f'[data-id="{node_id}"]').click()
            assert page.locator(f'[data-id="{node_id}"]').get_attribute("aria-pressed") == "true"
            assert page.locator("#inspector a").get_attribute("href").startswith("https://github.com/Requora/")
        page.locator('[data-view="imports"]').click()
        assert page.locator(".node").count() == 5
        assert page.locator(".edge.future").count() == 0
        assert page.locator(".edge").count() == 5
        page.locator('[data-id="order_source"]').focus()
        page.keyboard.press("Enter")
        assert page.locator('[data-id="order_source"]').get_attribute("aria-pressed") == "true"
        page.locator("#language").click()
    page.screenshot(path="/tmp/warehouse-progress-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-view="flow"]').click()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert page.locator(".map-scroll").evaluate("node => node.scrollWidth > node.clientWidth")
    page.screenshot(path="/tmp/warehouse-progress-mobile.png", full_page=True)
    assert not errors, errors
    browser.close()
print("PASS: two languages, both diagrams, 28 module selections, keyboard, mobile layout, no JS errors")
