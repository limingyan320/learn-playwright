from playwright.sync_api import sync_playwright,expect


with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    page = browser.new_page()
    page.goto("https://the-internet.herokuapp.com/login")

    page.get_by_label("username").fill("tomsmith")
    page.get_by_label("password").fill("SuperSecretPassword!")

    page.get_by_role(role="button",name = "Login").click()

    expect(page.get_by_text("You logged into a secure area!")).to_be_visible()
    input("\n")
