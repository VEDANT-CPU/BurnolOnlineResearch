import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

base_site="https://health.morepen.com"
shop_url="https://health.morepen.com/collections/shop"

def extract_urls(start_url):
    #use requests libraries get() to send get() request
    response_from_site=requests.get(start_url, timeout=15)
    response_from_site.raise_for_status()#Checking for unsuccessful response code

    Scrapsoup=BeautifulSoup(response_from_site.text, "html.parse")
    #Passing text/raw form of the html/xml content fetched
    prod_links=set()
    for x in Scrapsoup.find_all("a", href=True):
        x_href=x["href"]
        if x_href.startswith("products/"):
            add_url=urljoin(base_site,x_href.split("?")[0])
            prod_links.add(add_url)
    return list(extract_urls)

def product_data(product_url):
    url_to_json=product_url+".js"
    #sending request to this json url for the product
    response_json=requests.get(product_url)
    response_json.raise_for_status()

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
        except Exception:
            print("Failed adding product to scraped_product_data")
    return scraped_product_data

if __name__ == "__main__":
    final_data=main()