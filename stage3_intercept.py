from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    page = browser.new_page()
    page.goto("about:blank")

    input("\n") 
    predicate_whichisafunction= lambda response:"json" in response.url
    with page.expect_response(predicate_whichisafunction) as info: # 在页面中装监听器，准备配合进行AJAX的拦截
        page.evaluate("fetch('https://httpbin.org/json')") # 这里其实就是AJAX的执行了，page.evaluate 即 playwright 告诉浏览器去执行一段JS语句，这里的参数，也就是一整个字符串，就是一句JS

    # 响应到达，监听器过滤并捕获AJAX的返回并存入info
    response = info.value
    print(f"response整体:{response}")
    print(f"response.url:{response.url}")
    print(f"response.status:{response.status}")
    res = response.json()
    res = json.dumps(res,ensure_ascii = False,indent = 2)
    print(f"response.json:{res}")
    input("\n")
        
