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
import shortuuid
import os
import time

def get_scraperapi_url(url):
    return f'http://api.scraperapi.com?api_key={scraperapi_key}&url={url}'
# David: handling formats so that json.loads workds
def regex_handling(content):
        # Replace single quotes around keys with double quotes
    content = re.sub(r"'(\w+)':", r'"\1":', content)

    # Replace single quotes around string values with double quotes
    content = re.sub(r":\s*'([^']*)'", r': "\1"', content)

    # Replace escaped single quotes within strings to normal single quotes
    content = re.sub(r"\\'", r"'", content)

    # Replace single quotes around JSON boolean and null values with unquoted versions
    content = re.sub(r"'(true|false|null)'", r'\1', content)

    # Ensure correct formatting for boolean and null values without quotes
    content = re.sub(r'(\s|:)(true|false|null)(\s|,|})', r'\1"\2"\3', content)

    # Handle variables by replacing them with string placeholders using a single regex
    content = re.sub(r'(\burlMapOf\b|\bmapLatOf\b|\bmapLngOf\b)', r'"\1"', content)

    # Remove trailing commas (invalid in JSON)
    content = re.sub(r",\s*([\]}])", r'\1', content)
    #final pass i don't know why we need it
    content = re.sub(r"'([^']*)'", r'"\1"', content)
    return content

async def visit_and_scrape(url, browser):
    page = await browser.new_page()
    await page.goto(get_scraperapi_url(url), timeout=300000)
#     await page.goto(url, timeout=300000)
#     logging.info(f'Successfully Opened webpage {url}')
    # await page.goto(scraperapi_url, timeout=120000)
    await page.screenshot(path = 'screenshot.png')
    logging.info(f'Successfully Opened webpage {url}')
    page_content = await page.content()
    parser = HTMLParser(page_content)
    result_data_dictionary = {}
    #result_data_dictionary = grab_geo_location_data(parser, result_data_dictionary)
    result_data_dictionary = scrape_data_aviso(parser, result_data_dictionary)
    result_data_dictionary['url'] = url
    print(result_data_dictionary)
    return result_data_dictionary


#David: take out avisoinfo from html
def scrape_aviso(parser, dictionary):
    target_script = None
    script_content = None
    script_tags = parser.css('script')
    for script in script_tags:
        if script.text() and 'const avisoInfo =' in script.text():
            target_script = script
    if target_script:
        script_content = target_script.text()
    # parse through html and find file that contains avisoInfo
    aviso_info_match = re.search(r'const avisoInfo = ({.*?});', script_content, re.DOTALL)
    if aviso_info_match:
        aviso_info_str = aviso_info_match.group(1)
    dictionary = extract_aviso_info(script_content, dictionary)
    dictionary = building_or_unit(aviso_info_str, dictionary)
    return dictionary

def building_or_unit(aviso_info_str, dictionary):
    pattern = r'"units":\[.*\],'
    modified_info_str = re.sub(pattern, '', aviso_info_str)
    if aviso_info_str != modified_info_str:
        print("This is a building")
        dictionary["is_building"] = True
        #find the unit links inside parent property
        info_str_find_unit = re.search(pattern, aviso_info_str)

        if info_str_find_unit:
            print('Finding units inside building property')
            units_found = re.findall(r'"url":"(.*?)"', info_str_find_unit.group())
            
            if units_found:
                dictionary['unit_urls'] = units_found
                child_urls_modified = ['https://www.inmuebles24.com' + url for url in dictionary['unit_urls']]
                dictionary['unit_urls'] = ", ".join(child_urls_modified)
            else:
                print('No units found in the building property.')
                dictionary['unit_urls'] = ''
    else:
        print("This is a unit")
        dictionary["is_building"] = False
    return dictionary

def generate_building_id():
    return str(shortuuid.ShortUUID().random(length=22))

#David: update dictionary from avisoinfo
def scrape_data_aviso(data, dictionary):
    dictionary = scrape_aviso(data, dictionary)
    return dictionary

def extract_aviso_info(script_content, data):

    def extract_field(pattern, default=""):
        match = re.search(pattern, script_content)
        return match.group(1) if match else default

    def extract_field2(pattern, default=""):
        match = re.search(pattern, script_content)
        if match and match.lastindex >= 2:
            if match.group(1) == 'null' and match.group(2) == 'null':
                return ''
            return f"{match.group(1)} to {match.group(2)}"
        elif match:
            return match.group(1)
        else:
            return default

    def extract_field3(primary_pattern, fallback_patterns, default=""):
        # Try primary pattern
        result = extract_field(primary_pattern)
        if result != default:
            return result
        
        # If primary pattern fails, try fallback patterns
        for pattern in fallback_patterns:
            result = extract_field(pattern)
            if result != default:
                return result
        
        return default
 
    def grab_icon_data():
        #Grabs data based on posting type
        if data['posting_type'] == 'DEVELOPMENT':
        #parent property
            data['number_of_units'] = extract_field(r'"numberOfUnits":(\d+)')
            if data['number_of_units'] == "":
                data['number_of_units'] = 0
            data["latitude"] = extract_field(r'"geolocation":{"latitude":([-+]?[0-9]*\.?[0-9]+)')
            if data["latitude"] == "":
                data["latitude"] = "N/A"
            data["longitude"] = extract_field(r'"geolocation":\{"latitude":[-+]?[0-9]*\.?[0-9]+,"longitude":([-+]?[0-9]*\.?[0-9]+)')
            if data["longitude"] == "":
                data["longitude"] = "N/A"
            data["building_id"] = generate_building_id()
        else:
        #child property
            data['parking_lot'] = extract_field3(r'"label":"Estacionamiento","measure":null,"value":"(\d+)"',[r'(\d+)\s*estacionamiento', r'(\d+)\s*parking'])
            data['bathrooms'] = extract_field3(r'"label":"[Bb]año[s]?","measure":null,"value":"(\d+)"',[r'(\d+)\s*baño', r'(\d+)\s*bathroom'])
            data['half_bathrooms'] = extract_field(r'"label":"[Mm]edio baño[s]?","measure":null,"value":"(\d+)"')
            data['price'] = extract_field(r'"formattedAmount":"(.*?)"')
            data['bedrooms'] = extract_field3(r'"label":"Recámara","measure":null,"value":"(\d+)"',[r'(\d+)\s*recámara', r'(\d+)\s*bedroom'])
            data['age'] = extract_field(r'"label":"[aA]ntigüedad","measure":null,"value":"([^"]*)"')
            data['property_dimension(sqft)'] = extract_field3(
                r'"label":"Construido","measure":"(.*?)","value":"(\d+)"',
                [r'(\d+)\s*m²', r'(\d+)\s*sqft'])
            if data["price"] == "":
                data["price"] = "N/A"
            if data["parking_lot"] == "":
                data["parking_lot"] = 0
            if data['bedrooms'] == "":
                data['bedrooms'] = 0
            if data['age'] == "A estrenar":
                data['age'] = 0
            if data['half_bathrooms'] == "":
                data['half_bathrooms'] = 0
            if data["property_dimension(sqft)"] == "":
                data["property_dimension(sqft)"] = "N/A"

    # Extract key fields using regex
    #if it's unit property, we want to extract complete data

    data['title'] = extract_field(r'"title":"(.*?)"')
    data['generatedtitle'] = extract_field3(r'"generatedTitle":"(.*?)"',[r'"title":"(.*?)"'])
    data['description'] = extract_field(r'["\']description["\']\s*:\s*["\'](.*?)["\']')
    data['publication_date'] = extract_field(r"'publicationDateFormatted':\s*'(.*?)'")
    data['posting_type'] = extract_field(r"'postingType': '([^,]*)'")
    grab_icon_data()
    data['address'] = extract_field3(r'"postingLocation":{"address":{"name":"(.*?)","visibility":"EXACT"}',[r"'address':\s*\{[\"]name[\"]:[\"](.*?)[\"]"])
    data['pictures'] = re.findall(r'"resizeUrl1200x1200":"(.*?)"', script_content)
    data['property_type'] = extract_field(r'[\'"]realEstateType[\'"]:\s*\{[\'"]name[\'"]:\s*[\'"](.*?)[\'"]')
    data['operation_type'] = extract_field(r'"operationType":\s*\{"name":"(.*?)"')
    # data['Country'] = extract_field(r'"label":"PROVINCIA","depth":1,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['zone'] = extract_field(r'"label":"ZONA","depth":3,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['city'] = extract_field(r'"label":"CIUDAD","depth":2,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['postingid'] = extract_field3(r'"postingId":"(.*?)"',[r"'idAviso':\s*'(.*?)'"])
    data['postingcode'] = extract_field(r'[\"\']postingCode[\"\']\s*:\s*[\"\'](.*?)[\"\']')
    data['publisherid'] = extract_field(r"'publisherId':\s*'(\d+)'")
    data['premier'] = extract_field(r'[\"\']?premier[\"\']?\s*:\s*(true|false)')

    # Convert lists to comma-separated strings
    data['pictures'] = ", ".join(data['pictures']) 

    return data


