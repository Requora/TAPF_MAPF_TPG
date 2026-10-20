"""Browser QA for the served dashboard; requires the optional Playwright tool."""
import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    # 中文: 收集浏览器异常供最后断言, 避免页面外观正常却隐藏脚本错误.
    # English: Collect browser errors for a final assertion so a visible page cannot hide script failures.
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(sys.argv[1])
    assert response.status == 200
    for language in ("zh-CN", "en"):
        assert page.locator("html").get_attribute("lang") == language
        page.locator('[data-view="flow"]').click()
        assert page.locator(".node").count() == 15
        assert page.locator(".edge.future").count() == 10
        # 中文: 浏览器回调提取所有节点 ID, 逐一验证选择行为, 防止只测默认节点.
        # English: Extract all node IDs in the browser so selection is checked beyond the default node.
        for node_id in page.locator(".node").evaluate_all("nodes => nodes.map(n => n.dataset.id)"):
            page.locator(f'[data-id="{node_id}"]').click()
            assert page.locator(f'[data-id="{node_id}"]').get_attribute("aria-pressed") == "true"
            assert page.locator("#inspector a").get_attribute("href").startswith("https://github.com/Requora/")
        page.locator('[data-view="imports"]').click()
        assert page.locator(".node").count() == 11
        assert page.locator(".edge.future").count() == 0
        assert page.locator(".edge").count() == 16
        page.locator('[data-id="order_source"]').focus()
        page.keyboard.press("Enter")
        assert page.locator('[data-id="order_source"]').get_attribute("aria-pressed") == "true"
        page.locator("#language").click()
    page.screenshot(path="/tmp/warehouse-progress-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-view="flow"]').click()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    # 中文: 浏览器回调比较内部宽度, 确认小屏架构图能横向滚动而不撑破页面.
    # English: Compare inner widths to verify that the mobile diagram scrolls inside its container.
    assert page.locator(".map-scroll").evaluate("node => node.scrollWidth > node.clientWidth")
    page.screenshot(path="/tmp/warehouse-progress-mobile.png", full_page=True)
    assert not errors, errors
    browser.close()
print("PASS: two languages, both diagrams, 30 module selections, keyboard, mobile layout, no JS errors")
