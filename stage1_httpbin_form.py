from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    page = browser.new_page()
    page.goto("https://httpbin.org/forms/post")
    page.get_by_label("Customer name").fill("李名言")
    page.get_by_label("Telephone").fill("133123456789")
    page.get_by_label("E-mail address").fill("12901234567@qq.com")

    page.get_by_label("Large").check()
    page.get_by_label("Bacon").check()
    
    page.get_by_label("Preferred delivery time").fill("18:30")
    page.get_by_label("Delivery instructions").fill("xb")

    page.get_by_role(role = "button",name = "Submit order").click()
    input("\n")

