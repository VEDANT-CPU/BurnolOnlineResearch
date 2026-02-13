import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
from pathlib import Path
import csv
import time
from random import uniform
import cloudscraper

base_site="https://health.drmorepen.com"
shop_url="https://health.drmorepen.com/collections/shop"

def extract_urls(start_url):
    #use requests libraries get() to send get() request
    response_from_site=requests.get(start_url, timeout=15)
    response_from_site.raise_for_status()#Checking for unsuccessful response code
    print(response_from_site.status_code)
    print("Length of respons: ", len(response_from_site.text))

    Scrapsoup=BeautifulSoup(response_from_site.text, "html.parser")
    #Passing text/raw form of the html/xml content fetched
    prod_links=set()
    for x in Scrapsoup.find_all("a", href=True):
        x_href=x["href"]
        if x_href.startswith("/products/"):
            add_url=urljoin(base_site,x_href.split("?")[0])
            prod_links.add(add_url)
    return list(prod_links)

def product_data(product_url):
    url_to_json=product_url+".js"
    #sending request to this json url for the product
    HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}
    #my_scraper=cloudscraper.create_scraper()
    response_json=requests.get(url_to_json,headers=HEADERS, timeout=15)
    response_json.raise_for_status()
    print(response_json.status_code)
    print("Length of respons: ", len(response_json.text))

    prod_data=response_json.json()
    #now organise this prod_data into a dictionary
    info_products={
        "Product Title": prod_data["title"],
        "Description": prod_data["description"],
        "Vendor": prod_data["vendor"],
        "type": prod_data["type"],
        "price": prod_data["price"],
        "Variants": []
    }
    for variant in prod_data.get("variants", []):
        info_products["Variants"].append({
            "variant_title": variant.get("title"),
            "price": variant.get("price") / 100 if variant.get("price") else None,
            "compare_at_price": variant.get("compare_at_price") / 100 if variant.get("compare_at_price") else None,
            "sku": variant.get("sku"),
            "inventory_quantity": variant.get("inventory_quantity")
        })

    return info_products

#This is my scripts main pipeline.
def main():
    extracted_urls=[]
    extracted_urls=extract_urls(shop_url)
    print("No. of urls found: ", len(extracted_urls))
    scraped_product_data=[]

    for url in extracted_urls:
        try:
            scraped_product_data.append(product_data(url))
            time.sleep(uniform(2.0,4.0))#Hitting servers to fast, with every get request in loop
            #Do time.sleep
        except Exception:
            print("Failed adding product to scraped_product_data")
    save_dicts_to_csv_pandas(scraped_product_data, r"C:\Users\VEDANT\Desktop\BurnolOnlineResearch\EcommData.csv")
    return scraped_product_data

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
    final_data=[]
    final_data=main()