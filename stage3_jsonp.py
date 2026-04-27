from playwright.sync_api import sync_playwright
import json5
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    page = browser.new_page()
    page.goto("about:blank")

    predicate_whichisafuntion = lambda r: "suggestion.baidu.com" in r.url
    
    input("\n")
    with page.expect_response(predicate_whichisafuntion) as info:
        page.evaluate(
            """
            const s = document.createElement('script');
            s.src = 'https://suggestion.baidu.com/su?wd=python&cb=myCb';
            document.head.appendChild(s);
            """
        )
    response = info.value
    raw = response.text()
    print(f"raw原始:\n{raw}")
    # raw = "myCb({q:'python', p:false, s:[...]});"
    match = re.match(r'^\s*\w+\((.*)\);?\s*$',raw,re.DOTALL)
    if match is None:
        raise RuntimeError(f"卧槽没匹配上,你个蠢东西:{raw!r}")
    inside = match.group(1)
    res = json5.loads(inside)
    print(f"{res}")
    input("\n")
