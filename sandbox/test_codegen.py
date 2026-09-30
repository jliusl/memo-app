import re
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("https://www.ruanyifeng.com/blog/index.html")
    page.get_by_role("link", name="继续阅读全文 »").click()
    expect(page.get_by_role("link", name="阮一峰")).to_be_visible()
    expect(page.locator("#page-title")).to_contain_text("再见了，React Native")
    expect(page.locator("#main-content")).to_match_aria_snapshot("- strong: \"[通知] 下周五开始的中秋和十一假期，周刊休息。\"")