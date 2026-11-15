"""Browser QA for the served dashboard; requires the optional Playwright tool."""
import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    # 中文: pageerror 回调将浏览器报告的脚本异常存入 errors, 让最后的断言能发现页面外观正常时仍存在的错误.
    # English: The pageerror callback stores browser script errors in errors so the final assertion catches failures
    # even when the page looks correct.
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(sys.argv[1])
    assert response.status == 200
    for language in ("zh-CN", "en"):
        assert page.locator("html").get_attribute("lang") == language
        page.locator('[data-view="flow"]').click()
        assert page.locator(".node").count() == 16
        assert page.locator(".edge.future").count() == 10
        # 中文: evaluate_all 的回调通过 map 逐个读取架构图元素的模块 ID, 让测试循环检查每个模块的选择行为.
        # 这里的节点是代表软件模块的界面元素, 不是仓库地图中的机器人位置.
        # English: The evaluate_all callback uses map to read each diagram element's module ID so the test checks
        # selection for every module. These nodes represent software modules, not robot positions on the warehouse map.
        for node_id in page.locator(".node").evaluate_all("nodes => nodes.map(n => n.dataset.id)"):
            page.locator(f'[data-id="{node_id}"]').click()
            assert page.locator(f'[data-id="{node_id}"]').get_attribute("aria-pressed") == "true"
            assert page.locator("#inspector a").get_attribute("href").startswith("https://github.com/Requora/")
        page.locator('[data-view="imports"]').click()
        assert page.locator(".node").count() == 12
        assert page.locator(".edge.future").count() == 0
        assert page.locator(".edge").count() == 17
        page.locator('[data-id="order_source"]').focus()
        page.keyboard.press("Enter")
        assert page.locator('[data-id="order_source"]').get_attribute("aria-pressed") == "true"
        page.locator("#language").click()
    page.screenshot(path="/tmp/warehouse-progress-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-view="flow"]').click()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    # 中文: evaluate 的回调比较架构图容器的内容宽度和可见宽度, 让断言确认小屏中存在横向滚动区域.
    # 上一条断言另行检查整个页面没有横向溢出, 两项检查共同验证架构图只在自己的容器内滚动.
    # English: The evaluate callback compares the diagram container's content and visible widths to confirm horizontal scrolling.
    # The preceding assertion separately checks page overflow; together they verify that scrolling stays inside the container.
    assert page.locator(".map-scroll").evaluate("node => node.scrollWidth > node.clientWidth")
    page.screenshot(path="/tmp/warehouse-progress-mobile.png", full_page=True)
    assert not errors, errors
    browser.close()
print("PASS: two languages, both diagrams, 32 module selections, keyboard, mobile layout, no JS errors")
