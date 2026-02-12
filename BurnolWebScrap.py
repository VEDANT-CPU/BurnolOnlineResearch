from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    # options.add_argument("--headless")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)#when u call Chrome like this
    #Selenium excepts chromedriver to already exist and match with your chrome version
    """stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
        helps against naive checks like navigator.webdriver, navigator.vendor and navigator.languages"""
    #print("navigator.webdriver:", driver.execute_script("return navigator.webdriver"))
#driver.execute_script() runs javascript inside browser.
# return navigator.webdriver is a javascript command to get value of navigator.webdriver
#It askes if the browser requesting is controlled by a webdriver.Standard check in many websites
    #print("navigator.userAgent: ", driver.execute_script("return navigator.userAgent"))
# checks for browser type, version, OS and headless or not
#headless means get request without rendering a frontend/GUI which means not a human browser
    """print("Title: ", driver.title)
    ps = driver.page_source
    print("Page source length: ", len(ps))
    print("Contains Burnol? ", "Burnol" in ps)
    return driver"""
    return driver

#driver.quit()
def scrape_page(driver):
    url = "https://www.morepen.com/"
    driver.get(url)
    html_content = driver.page_source
    print("Page Source Length: ", len(html_content))

def main():
    driver = create_driver()
    html_var = driver.page_source


    try:
        print("navigator.webdriver:", driver.execute_script("return navigator.webdriver"))
        print("navigator.userAgent: ", driver.execute_script("return navigator.userAgent"))
        ps = driver.page_source
        print("Page source length: ", len(ps))
        print("Contains Burnol? ", "Burnol" in ps)
    finally:
        driver.quit()# Terminate the webdriver session


if __name__ == "__main__":
     main()
