from bs4 import BeautifulSoup
import requests

more_pen_url = 'https://www.morepen.com/aboutus'
#requests.get(more_pen_url)

#websites block automated python requests. we need to make it mimic Chrome!!
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(more_pen_url, headers=headers)
print(response.status_code)
print(response.text[:500])#to print first 500 chars of the response object received from requests.get
#stored in the response variable.