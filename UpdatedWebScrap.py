# BurnolWebScrap.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from random import uniform
import time
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import json
import csv
import os

BASE_DOMAIN = "morepen.com"
BASE_WEBSITE = "https://www.morepen.com"
API_PAGE = "https://www.morepen.com/api"


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # avoid headless while debugging

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def polite_sleep(a=1.5, b=3.0):
    time.sleep(uniform(a, b))


def scrape_page(driver, url):
    """
    Load the page using selenium (so JS is rendered) and return rendered HTML.
    """
    driver.get(url)
    polite_sleep(2.0, 4.0)
    return driver.page_source


def extract_internal_links(html_content, base_url=BASE_WEBSITE):
    """
    Extract all internal links from the rendered HTML.
    Returns a deduped list of absolute URLs (no fragments).
    """
    soup = BeautifulSoup(html_content, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        # only keep morepen domain (this includes subdomains like something.morepen.com if needed)
        if parsed.netloc.endswith(BASE_DOMAIN):
            clean = absolute.split("#")[0]
            links.add(clean)
    return sorted(links)


def classify_links(links):
    """
    From a list of internal links, decide which are likely product pages and which are PDF files.
    Heuristics:
      - .pdf extensions -> pdf_links
      - links containing '/api/' -> product_links (preferred for corporate API pages)
      - fallback: links containing 'product' or '/products/' in path
    Returns (product_links, pdf_links)
    """
    product_links = []
    pdf_links = []

    for link in links:
        parsed = urlparse(link)
        path = parsed.path.lower()

        # PDFs
        if path.endswith(".pdf") or ".pdf" in parsed.query.lower():
            pdf_links.append(link)
            continue

        # Prefer links under /api/ (corporate API / bulk product pages often use this)
        if "/api/" in path or path.startswith("/api"):
            product_links.append(link)
            continue

        # Fallback heuristics for product-like paths
        if "product" in path or "/products/" in path:
            product_links.append(link)
            continue

    # dedupe
    return sorted(set(product_links)), sorted(set(pdf_links))


def find_json_ld(soup):
    """
    Try to find application/ld+json structured product data and parse it.
    Returns dict or None.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text or len(text.strip()) == 0:
                continue
            data = json.loads(text.strip())
            # data can be list or dict
            if isinstance(data, list):
                # find the first Product object
                for item in data:
                    if item.get("@type", "").lower() in ("product", "productcollection", "product"):
                        return item
            elif isinstance(data, dict):
                if data.get("@type", "").lower() in ("product", "productcollection", "product"):
                    return data
                # sometimes page contains "mainEntity" etc
                if "mainEntity" in data and isinstance(data["mainEntity"], dict):
                    me = data["mainEntity"]
                    if me.get("@type", "").lower() == "product":
                        return me
        except Exception:
            continue
    return None


def extract_section_after_heading(soup, heading_keywords):
    """
    Generic helper: find headings (h2,h3,h4,strong) containing any keyword and return
    following sibling text blocks (joined). Returns first match only.
    """
    headings = soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"])
    for hd in headings:
        text = (hd.get_text(" ", strip=True) or "").lower()
        for kw in heading_keywords:
            if kw in text:
                # gather siblings until next heading
                parts = []
                nxt = hd.find_next_sibling()
                # gather several siblings if they are paragraphs or lists
                while nxt and nxt.name not in ["h1", "h2", "h3", "h4", "strong", "b"]:
                    if nxt.get_text(strip=True):
                        parts.append(nxt.get_text(" ", strip=True))
                    nxt = nxt.find_next_sibling()
                return " ".join(parts).strip()
    return ""


def extract_product(driver, product_url):
    """
    Visit a corporate product page and extract robust fields.
    Returns dictionary with common fields.
    """
    driver.get(product_url)
    polite_sleep(2.0, 4.0)
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
    jld = find_json_ld(soup)
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
    data["composition"] = extract_section_after_heading(soup, ["composition", "ingredients", "active ingredient", "active ingredients"])
    data["usage_indications"] = extract_section_after_heading(soup, ["indication", "uses", "usage", "indications"])
    data["dosage"] = extract_section_after_heading(soup, ["dosage", "direction", "directions", "how to use", "dose"])

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
        html = scrape_page(driver, API_PAGE)
        links = extract_internal_links(html, base_url=API_PAGE)
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


if __name__ == "__main__":
    main()
