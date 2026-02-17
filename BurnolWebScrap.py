from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from random import uniform
import time
import os
import csv
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
from pathlib import Path
import pandas as pd

base_url="https://morepen.com"
api_url="https://morepen.com/api"
domain="morepen.com"
prod_keywords=["products", "api", "formulations", "product","productcollection", "dossier"]

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
    url = "https://www.morepen.com/api"
    driver.get(url)
    html_content = driver.page_source
    print("Page Source Length: ", len(html_content))

    time.sleep(uniform(2,4))
    return html_content

def extract_internal_links(html_content, base_url="https://www.morepen.com/"):
    #To return a list of absolute url from the rendered html
    ScrapSoup = BeautifulSoup(html_content, "html.parser")#Entire page organized into DOM tree
    #for searching and retrieval of content. Tags which are themselves subtrees in this.
    links = set() #To ensure there are no duplicates

    for x in ScrapSoup.find_all("a",href=True):
        link_href = x["href"]

        target_url = urljoin(base_url, link_href)
        parsed_url = urlparse(target_url)#converts the target_url which is ordinary url
        #to a dictionary like structure having 6 attributes
        if parsed_url.netloc.endswith(domain):
            links.add(target_url.split("#")[0])
    return list(links) #sorted(links)

def classify_links(links):
    product_links = []
    pdf_links = []

    for link in links:
        parsed = urlparse(link)
        path = parsed.path.lower()
        if path.endswith(".pdf"):
            pdf_links.append(link)
            continue
        if "api" in path or path.beginswith("/api"):
            product_links.append(link)
            continue
        if "product" in path or "/products/" in path:
            product_links.append(link)
            continue
        
    return set(product_links), set(pdf_links) #This will return a tuple.

def json_ld(soup):
    for scrip in soup.find_all("script", type="application/ld+json"):
        try:
            text=scrip.string
            if not text:
                return
            data=json.loads(text.strip())#.strip() to remove whitespace and \n char from start and end
            if isinstance(data, list):
                for item in data:
                    if item.get("@type").lower() in prod_keywords:
                        return item
            elif isinstance(data, dict):
                if data.get("@type").lower() in prod_keywords:
                    return data
        except Exception:
            continue
    return None

def section_after_heading(soup, heading_keywords):
    headings=["h1","h2","h3","strong","b","h4"]
    head_tags = soup.find_all(headings)
    for head in head_tags:
        tag_text=(head.get_text(" ",strip=True) or "").lower()
        for kw in heading_keywords:
            if kw in tag_text:
                nxt_tag = head.find_next_sibling()
                add_part = []
                while nxt_tag and nxt_tag.name not in headings:
                    if nxt_tag.get_text(strip=True):
                        add_part.append(nxt_tag.get_text(" ",strip=True))
                        nxt_tag = nxt_tag.find_next_sibling()
                return " ".join(add_part).strip()
    return ""

def extract_product(driver, product_url):
    """
    Visit a corporate product page and extract robust fields.
    Returns dictionary with common fields.
    """
    driver.get(product_url)
    time.sleep(2.0, 4.0)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    data = {
        "url": product_url,
        "product_name": "",
        "short_description": "",
        "detailed_description": "",
        "composition": "",
        "usage_indications": "",
        "dosage": "",
        "other_info": ""
    }

    # 1) Try structured JSON-LD first (best source if present)
    jld = json_ld(soup)
    if jld:
        data["product_name"] = jld.get("name") or jld.get("headline") or ""
        data["short_description"] = jld.get("description", "") or ""
        # price/offers if present
        offers = jld.get("offers") or {}
        if isinstance(offers, dict):
            data["other_info"] += f"price:{offers.get('price','')} {offers.get('priceCurrency','')}; "
    # 2) Fallback to DOM scraping
    if not data["product_name"]:
        # Prefer a product container heading (h1/h2) inside main content
        h1 = soup.find(["h1", "h2"], recursive=True)
        if h1:
            data["product_name"] = h1.get_text(" ", strip=True)

    # Collect longer paragraphs as descriptions
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
    if paragraphs:
        data["short_description"] = paragraphs[0]
        data["detailed_description"] = " ".join(paragraphs[:4])

    # Section-based extraction using keywords (composition / ingredients / dosage / indication / usage)
    data["composition"] = section_after_heading(soup, ["composition", "ingredients", "active ingredient", "active ingredients"])
    data["usage_indications"] = section_after_heading(soup, ["indication", "uses", "usage", "indications"])
    data["dosage"] = section_after_heading(soup, ["dosage", "direction", "directions", "how to use", "dose"])

    # As a fallback, find any lists that might contain composition bullets
    if not data["composition"]:
        ul = soup.find("ul")
        if ul:
            items = [li.get_text(" ", strip=True) for li in ul.find_all("li")]
            if items and len(" ".join(items)) > 30:
                data["composition"] = "; ".join(items[:10])

    # Clean whitespace
    for k, v in data.items():
        if isinstance(v, str):
            data[k] = " ".join(v.split())

    return data


def download_pdf(pdf_url, save_dir="pdfs"):
    """
    Download PDF with requests and save under save_dir. Returns filename or None.
    """
    os.makedirs(save_dir, exist_ok=True)
    try:
        resp = requests.get(pdf_url, timeout=20)
        resp.raise_for_status()
        filename = pdf_url.split("/")[-1].split("?")[0] or "download.pdf"
        path = os.path.join(save_dir, filename)
        with open(path, "wb") as f:
            f.write(resp.content)
        print("[PDF] downloaded:", path)
        return path
    except Exception as e:
        print("[PDF] failed:", pdf_url, e)
        return None


def save_products_to_csv(products, filename="products_morepen.csv"):
    keys = ["url", "product_name", "short_description", "detailed_description", "composition", "usage_indications", "dosage", "other_info"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for p in products:
            row = {k: p.get(k, "") for k in keys}
            writer.writerow(row)
    print("[Saved CSV]", filename)


def main():
    driver = create_driver()
    try:
        # start at the API page explicitly
        html = scrape_page(driver)
        links = extract_internal_links(html, base_url=api_url)
        print("All internal links extracted from API page:", len(links))

        product_links, pdf_links = classify_links(links)
        print("Product candidates:", len(product_links))
        print("PDF candidates:", len(pdf_links))

        # Extract product info
        products = []
        for idx, p_url in enumerate(product_links, start=1):
            try:
                print(f"[{idx}/{len(product_links)}] Processing product:", p_url)
                pdata = extract_product(driver, p_url)
                products.append(pdata)
            except Exception as e:
                print("product extraction failed for", p_url, e)

        # Download found PDFs
        for pdf in pdf_links:
            download_pdf(pdf)

        # Save data
        if products:
            save_products_to_csv(products)

    finally:
        driver.quit()

def save_dicts_to_csv(dict_list, filepath, fieldnames=None):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    if not dict_list:
        print("No rows to save for", filepath); return
    if fieldnames is None:
        # infer keys from first dict
        fieldnames = list(dict_list[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in dict_list:
            writer.writerow({k: (v if v is not None else "") for k,v in row.items()})

# alternative (pandas)
def save_dicts_to_csv_pandas(dict_list, filepath):
    df = pd.DataFrame(dict_list)
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8")

if __name__ == "__main__":
    main()
