from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from random import uniform
import time
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse


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

    time.sleep(uniform(2,4))
    return html_content

def extract_internal_links(html_content, base_url="https://www.morepen.com/"):
    ScrapSoup = BeautifulSoup(html_content, "html.parser")#Entire page organized into DOM tree
    #for searching and retrieval of content. Tags which are themselves subtrees in this.
    links = set() #To ensure there are no duplicates

    for x in ScrapSoup.find_all("a",href=True):
        link_href = x["href"]

        target_url = urljoin(base_url, link_href)
        parsed_url = urlparse(target_url)#converts the target_url which is ordinary url
        #to a dictionary like structure having 6 attributes
        if parsed_url.netloc.endswith("morepen.com"):
            links.add(target_url.split("#")[0])
    return list(links)

def classify_links(links):
    product_links = []
    pdf_links = []

    for link in links:
        parsed = urlparse(link)
        path = parsed.path.lower()
        if path.endswith(".pdf"):
            pdf_links.append(link)
        elif "product" in path or "api" in path:
            product_links.append(link)
    return product_links, pdf_links #This will return a tuple.

def extract_product(html_content, param_url):
    Mysoup = BeautifulSoup(html_content, "html.parser")
    data = {
        "url": param_url,
        "Prod_name": "",
        "About": "",
        "use": "",
    }


def main():
    driver = create_driver()
    html_content = scrape_page(driver)
    links = extract_internal_links(html_content)
    print("No. of links: ", len(links))

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
