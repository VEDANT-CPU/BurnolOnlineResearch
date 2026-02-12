from selenium import webdriver
from selenium.common.exceptions import WebDriverException
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)  # Selenium Manager will try to fetch driver
print(driver.title)
driver.quit()
