from playwright.sync_api import sync_playwright
import re
import json
import base64

with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    context = browser.new_context(ignore_https_errors = True)
    page = context.new_page()
    try:
        page.goto("https://inv-veri.chinatax.gov.cn") 
        
        input("\n")
        page.locator("#fphm").fill("25377000000496974821")
        page.locator("#kprq").fill("20251024")

        # captcha = page.locator("#yzm_img")
        # captcha.wait_for(state = "visible")
        # captcha.screenshot(path = "img/captcha.png")
        predicate_whichisafunction = lambda r:"yzmQuery" in r.url
        with page.expect_response(predicate_whichisafunction) as info:
            page.locator("#kjje").fill("24")
        

        captcha = info.value
        # print(f"captha:{captcha}")
        raw = captcha.text()
        match = re.match(r'^\s*\w+\((.*)\)\s*$',raw,re.DOTALL)
        if match is None:
            raise RuntimeError(f"匹配失败你个脑残:{raw!r}")
        inside = match.group(1)

        data = json.loads(inside)
        img_byte = base64.b64decode(data["key1"])
        with open("img/captcha.jpg","wb") as f:
            f.write(img_byte)
        answer = input("请看 img/captcha.jpg，输入验证码后回车：")

        page.locator("#yzm").fill(answer)
        page.locator("#yzm").press("Tab")
        
        with page.expect_response(lambda r:"vatQuery" in r.url and r.status == 200) as info:
            page.locator("#checkfp").click()

        result_raw = info.value.text()
        print(f"vatQuery原始响应：{result_raw}")
    finally:
        input("回车关闭。。。")
    
