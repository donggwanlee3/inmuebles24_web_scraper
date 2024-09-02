import re
import json
import asyncio
import aiohttp
import chompjs
import logging
from pathlib import Path
from urllib.parse import urljoin
from selectolax.parser import HTMLParser
from playwright.async_api import async_playwright
from helper import visit_and_scrape
import csv
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from scripts import aws
import pandas as pd
import config
import shutil
# Load environment variables from the .env file
load_dotenv()
scraperapi_key = os.getenv('SCRAPERAPI')

num_of_pages = 1000
unit_data = []
building_data = []
processed_urls = set()
child_urls = []

def get_scraperapi_url(url):
    return f'http://api.scraperapi.com?api_key={scraperapi_key}&url={url}'

# Scrape 20 properties from the {page_num}
async def scrape_listing_links(url, page_num):
    async with async_playwright() as pw:
        browser = None
        try:
            # Attempt to connect to the browser using the proxy URL
            browser = await pw.chromium.launch()
            print("Connected to launched successfully!")
        except Exception as e:
            # If connection fails, print an error message
            print(f"Failed to connect to browser: {e}")
            print("See if your proxy is correct or didn't run out of data")

        page = await browser.new_page()

        modified_url = url.replace(".html", f"-pagina-{page_num}.html")
        print(modified_url)
        try:
            await page.goto(get_scraperapi_url(modified_url), timeout=120000)
        except Exception as e:
            print(f"An error occurred: {e}")
        print(f'Successfully Opened Inmuebles24 page:{page_num}')
        listing_elements = await page.query_selector_all('div[data-to-posting]')
        print(f'Found {len(listing_elements)} listing elements')

        hrefs = []
        for element in listing_elements:
            try:
                href = await element.get_attribute('data-to-posting')
                if href:
                    hrefs.append(href)
            except Exception as e:
                print(f'Error retrieving attribute: {e}')

        await browser.close()

        base_url = 'https://www.inmuebles24.com'
        absolute_hrefs = [urljoin(base_url, href) for href in hrefs]

        return absolute_hrefs

# pop one element from the list of urls, see the amount of properties, and then try to figure out if the properties in that 
# certain area is greater than 20000 properties. If they are, divide into subregion and add them 
# to the data. if they are not, find out how many pages are there and process the region using 
async def process_regions_bfs(list_urls):
    global child_urls
    while len(list_urls) != 0:
        base_url = list_urls.pop(0)
        print(f'going to url {base_url}')
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(get_scraperapi_url(base_url), timeout=300000)
            except Exception as e:
                print(f"An error occurred: {e}")
                continue
            page_content = await page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            # Extract the number of properties
            h1_element = soup.select_one('h1.Title-sc-1oqs0ed-0')
            if h1_element:
                text_content = h1_element.get_text()
                number_str = text_content.split(' ')[0]
                number_str = number_str.replace(',', '')  # Remove commas from the string
                number_of_properties = int(number_str)  # Convert the string to an integer
                print(f'found {number_of_properties} properties')

                # If the number of properties is greater than 20,000, extract hrefs
                if number_of_properties > 20000:
                    related_content_div = soup.select_one('div.SeoRelatedContentContainer-sc-1n58n0i-0')
                    if related_content_div:
                        base_url = 'https://www.inmuebles24.com'
                        # Find all ul elements with the specified class
                        ul = related_content_div.find('ul', class_='ItemList-sc-1n58n0i-2 fhDfYS')
                        if ul:
                            # Collect all the links within each ul
                            for a in ul.find_all('a', href=True):
                                list_urls.append(urljoin(base_url, a['href']))
    
                        print(list_urls)
                else:
                    page_numbers = number_of_properties // 20
                    if number_of_properties % 20 != 0:
                        page_numbers += 1
                    # should i process through all the page numbers and then go through each list?
                    for page_number in range(1, page_numbers + 1):
                        region_urls = []
                        browser = await pw.chromium.launch()
                        links = await scrape_listing_links(base_url, page_number)
                        region_urls.extend(links)
                        for each_url in region_urls:
                            print(f'Visiting listing URL: {each_url}')
                            try: 
                                await process_listing(each_url, browser)
                            except Exception as e:
                                print(f"An error occurred: {e}")
                        print("child_urls")
                        for child_url in child_urls:
                            child_url = child_url.strip()
                            print(f'Visiting listing URL: {child_url}')
                            try: 
                                await process_listing(child_url, browser)
                            except Exception as e:
                                print(f"An error occurred: {e}")                  
                        await browser.close()
    

async def add_parent_id():
    # Load the datasets
    unit_properties_df = pd.read_csv(config.unit_properties_path)
    building_properties_df = pd.read_csv(config.parent_properties_path)

    # Ensure 'unit_urls' is split correctly into lists
    building_properties_df['unit_urls'] = building_properties_df['unit_urls'].apply(lambda x: x.split(',') if isinstance(x, str) else [])

    # Create a mapping dictionary for URL to Longitude and Latitude
    url_to_info = {}
    for index, row in building_properties_df.iterrows():
        for url in row['unit_urls']:
            if url in url_to_info:
                continue
            url_to_info[url.strip()] = {
                'parent_id': row['building_id']
            }

    # Initialize the Longitude, Latitude, and Parent ID columns in unit_properties_df
    unit_properties_df['parent_id'] = unit_properties_df['url'].map(lambda x: url_to_info.get(x, {}).get('parent_id', None))
    # Save the updated dataframe to the existing CSV file
    unit_properties_df.to_csv(config.unit_properties_path , index=False)


#Iterate through pages from 1-1000, go to the website and take 20 listings from it
# , and write it into the csv file "data" if the property is individual property, and 
# write it into "parent_data" if the property is parent property
async def main():
    global unit_data, building_data
    backup_files()
    await process_regions_bfs(['https://www.inmuebles24.com/inmuebles.html'])
    await add_parent_id()
    await aws.upload_aws()


def backup_files():
    backup_file(config.parent_properties_path)
    backup_file(config.unit_properties_path)

def backup_file(file_path):
    backup_path = file_path + ".bak"
    if os.path.exists(file_path):
        shutil.copy(file_path, backup_path)

#Just going through one website. Testing function
async def one_website():
    listing_url = 'https://www.inmuebles24.com/propiedades/clasificado/alclapin-renta-de-amplio-departamento-en-cuadrante-neuchatel-143667020.html'
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        await process_listing(listing_url, browser)

        # print(absolute_hrefs)
        await browser.close()

async def process_listing(url, browser):
    global unit_data, building_data, processed_urls, child_urls
    # load new page and go get html file
    result_dictionary = await visit_and_scrape(url, browser)
    
    if result_dictionary != None:
        if url in processed_urls:
            return
        processed_urls.add(result_dictionary["url"])
        if result_dictionary["is_building"]:
            result_dictionary.pop("is_building", None)
            row_child_urls = result_dictionary['unit_urls']
            row_child_urls = row_child_urls.split(',')
            child_urls.extend(row_child_urls)
            building_data.append(result_dictionary)
            with open(config.parent_properties_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=building_data[0].keys())
                writer.writeheader()
                writer.writerows(building_data)  
        else:
            result_dictionary.pop("is_building", None)
            unit_data.append(result_dictionary)  
            with open(config.unit_properties_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=unit_data[0].keys())
                writer.writeheader()
                writer.writerows(unit_data)
    


asyncio.run(main())

 