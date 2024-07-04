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


auth = 'brd-customer-hl_acb2eb9e-zone-immutable24:wy51wnvm50zu'
browser_url = f'https://{auth}@brd.superproxy.io:9222'
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
    await page.goto(url, timeout=300000)
#     await page.goto(url, timeout=300000)
#     logging.info(f'Successfully Opened webpage {url}')
    # await page.goto(scraperapi_url, timeout=120000)
    logging.info(f'Successfully Opened webpage {url}')
    page_content = await page.content()
    parser = HTMLParser(page_content)
    result_data_dictionary = {}
    #result_data_dictionary = grab_geo_location_data(parser, result_data_dictionary)
    result_data_dictionary = scrape_data_aviso(parser, result_data_dictionary)
    result_data_dictionary['URL'] = url
    print(result_data_dictionary)
    return result_data_dictionary


#David: take out avisoinfo from html
def scrape_aviso(parser, dictionary):
    script_tags = parser.css('script')
    target_script = None
    for script in script_tags:
        if script.text() and 'const avisoInfo =' in script.text():
            target_script = script
            break
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
                dictionary['Unit Urls'] = units_found
                child_urls_modified = ['https://www.inmuebles24.com' + url for url in dictionary['Unit Urls']]
                dictionary['Unit Urls'] = ", ".join(child_urls_modified)
            else:
                print('No units found in the building property.')
                dictionary['Unit Urls'] = ''
    else:
        print("This is a unit")
        dictionary["is_building"] = False
    return dictionary


#David: update dictionary from avisoinfo
def scrape_data_aviso(data, dictionary):
    dictionary = scrape_aviso(data, dictionary)
    return dictionary


"""
Sean's implementation of extracting aviso infomation using regex
script_content: avisoInfo
data: dictionary containing all values neede

returns: dictionary 

WIP Problems:
    Cannot obtain geolocation data now after switching to scraperapi

    Parent: 
        Where to obtain age, most cases age is not included in the parent property but in child
        Same as Parking Lots

    Child:

Overall:
    Child is good to go
    Parent needs a bit more work
    Both needs to geolocation implemented in possible
    
"""
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
        if data['Posting Type'] == 'DEVELOPMENT':
        #parent property
            data['# of Units'] = extract_field(r'"numberOfUnits":(\d+)')
            if data['# of Units'] == "":
                data['# of Units'] = 0
            data["Latitude"] = extract_field(r'"geolocation":{"latitude":([-+]?[0-9]*\.?[0-9]+)')
            if data["Latitude"] == "":
                data["Latitude"] = "N/A"
            data["Longitude"] = extract_field(r'"geolocation":\{"latitude":[-+]?[0-9]*\.?[0-9]+,"longitude":([-+]?[0-9]*\.?[0-9]+)')
            if data["Longitude"] == "":
                data["Longitude"] = "N/A"
            # data['Bathrooms'] = extract_field2(r'"bathrooms":\{"tuple0":([^,]*),"tuple1":([^}]*)\}')
            # if data['Bathrooms'] == "":
            #     data['Bathrooms'] = "N/A"
            # data['Bedrooms'] = extract_field2(r'"rooms":\{"tuple0":([^,]*),"tuple1":([^}]*)\}')
            # if data['Bedrooms'] == "":
            #     data['Bedrooms'] = "N/A"
        else:
        #child property
            data['Parking Lot'] = extract_field3(r'"label":"Estacionamiento","measure":null,"value":"(\d+)"',[r'(\d+)\s*estacionamiento', r'(\d+)\s*parking'])
            data['Bathrooms'] = extract_field3(r'"label":"[Bb]año[s]?","measure":null,"value":"(\d+)"',[r'(\d+)\s*baño', r'(\d+)\s*bathroom'])
            data['Half Bathrooms'] = extract_field(r'"label":"[Mm]edio baño[s]?","measure":null,"value":"(\d+)"')
            data['Price'] = extract_field(r'"formattedAmount":"(.*?)"')
            data['Bedrooms'] = extract_field3(r'"label":"Recámara","measure":null,"value":"(\d+)"',[r'(\d+)\s*recámara', r'(\d+)\s*bedroom'])
            data['Age'] = extract_field(r'"label":"[aA]ntigüedad","measure":null,"value":"([^"]*)"')
            data['Property Dimension(sqft)'] = extract_field3(
                r'"label":"Construido","measure":"(.*?)","value":"(\d+)"',
                [r'(\d+)\s*m²', r'(\d+)\s*sqft'])
            if data["Price"] == "":
                data["Price"] = "N/A"
            if data["Parking Lot"] == "":
                data["Parking Lot"] = 0
            if data['Bedrooms'] == "":
                data['Bedrooms'] = 0
            if data['Age'] == "A estrenar":
                data['Age'] = 0
            if data['Half Bathrooms'] == "":
                data['Half Bathrooms'] = 0
            if data["Property Dimension(sqft)"] == "":
                data["Property Dimension(sqft)"] = "N/A"

    # Extract key fields using regex
    #if it's unit property, we want to extract complete data

    data['Title'] = extract_field(r'"title":"(.*?)"')
    data['GeneratedTitle'] = extract_field3(r'"generatedTitle":"(.*?)"',[r'"title":"(.*?)"'])
    data['Description'] = extract_field(r'["\']description["\']\s*:\s*["\'](.*?)["\']')
    # data['Seller'] = extract_field(r"'name':\s*'(.*?)'")
    data['Publication Date'] = extract_field(r"'publicationDateFormatted':\s*'(.*?)'")
    data['Posting Type'] = extract_field(r"'postingType': '([^,]*)'")
    grab_icon_data()
    data['Address'] = extract_field3(r'"postingLocation":{"address":{"name":"(.*?)","visibility":"EXACT"}',[r"'address':\s*\{[\"]name[\"]:[\"](.*?)[\"]"])
    data['Pictures'] = re.findall(r'"resizeUrl1200x1200":"(.*?)"', script_content)
    data['Property Type'] = extract_field(r'[\'"]realEstateType[\'"]:\s*\{[\'"]name[\'"]:\s*[\'"](.*?)[\'"]')
    data['Operation Type'] = extract_field(r'"operationType":\s*\{"name":"(.*?)"')
    # data['Country'] = extract_field(r'"label":"PROVINCIA","depth":1,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['Zone'] = extract_field(r'"label":"ZONA","depth":3,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['City'] = extract_field(r'"label":"CIUDAD","depth":2,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
    data['postingId'] = extract_field3(r'"postingId":"(.*?)"',[r"'idAviso':\s*'(.*?)'"])
    data['postingCode'] = extract_field(r'[\"\']postingCode[\"\']\s*:\s*[\"\'](.*?)[\"\']')
    data['publisherId'] = extract_field(r"'publisherId':\s*'(\d+)'")
    data['premier'] = extract_field(r'[\"\']?premier[\"\']?\s*:\s*(true|false)')

    # Convert lists to comma-separated strings
    data['Pictures'] = ", ".join(data['Pictures']) 

    return data


#Grabbing geo_location_data WIP b/c of some sort of html error w/ page
def grab_geo_location_data(parser, data):
    img = parser.css_first('img#static-map')
    if img:
        img_src = img.attributes.get('src')
        pattern = r'center=(-?\d+\.\d+),(-?\d+\.\d+)'
        lng_and_lat = re.search(pattern, img_src)
        print(lng_and_lat)
        data["Latitude"] = lng_and_lat.group(1)
        data["Longitude"] = lng_and_lat.group(2)
    else:
        data["Latitude"] = ""
        data["Longitude"] = ""
    return data

# # David: it's a helper function to scrape data from the parameter {url}
# async def visit_and_scrape(url, browser):
#     # try:
#     page = await browser.new_page()
#     await page.goto(url, timeout=300000)
#     logging.info(f'Successfully Opened webpage {url}')

#     page_content = await page.content()
#     parser = HTMLParser(page_content)
#     with open('page_content.html', 'w', encoding='utf-8') as file:
#             file.write(page_content)
#     result_data_dictionary = {}
#     # result_data_dictionary = extract_data_helper(parser)
#     result_data_dictionary = scrape_data_aviso(parser, result_data_dictionary)
#     result_data_dictionary['URL'] = url
#     print(result_data_dictionary)
#     return result_data_dictionary
#     # except Exception as e:
#     #     logging.error(f"Error in scrape_listing_data: {url}")
#     #     return None
# # Function to extract text using CSS selectors
# def extract_text(parser, selectors):
#     for selector in selectors:
#         element = parser.css_first(selector)
#         if element:
#             return element.text().strip()
#     return None
# # Extract numeric value
# def extract_numeric_value(text, keyword):
#     if text:
#         match = re.search(r'(\d+(?:\.\d+)?)', text)
#         return float(match.group(1)) if match else None
#     return None

# def get_icon_data(parser, keyword_map):
#     """Extracts icon data based on the given keyword map and parser."""
#     result = {}
#     for key, (keyword, base_selector, count) in keyword_map.items():
#         selectors = [base_selector.format(i+1) for i in range(count)]
#         value = next((extract_numeric_value(extract_text(parser, [selector]), keyword)
#                       for selector in selectors if extract_text(parser, [selector])),
#                      False if key == 'unidades' else None)
#         result[key] = value
#     return result
# #scraping from the icons and div
# def extract_data_helper(parser):

#             # Extract title
#             title = extract_text(parser, ["#article-container > h1", "#article-container > h2"])
#             logging.info(f"Title: {title}")

#             # Extract status and availability
#             status = extract_text(parser, ["#article-container > div.status-delivery-and-financing > div > div.item.IN_PROGRESS > div > span"])
#             availability = extract_text(parser, ["#article-container > div.status-delivery-and-financing > div > span.label"])
#             logging.info(f"Status: {status}")
#             logging.info(f"Availability: {availability}")

#             # Extract price
#             price = extract_text(parser, [
#                 "#article-container > div.pc-container > div > div > div > span > span:nth-child(3)",
#                 "#article-container > div.price-container-property > div > div.price-value > span:nth-child(1) > span > font > font"
#             ])
#             logging.info(f"Price: {price}")

#             # Extract location
#             location = extract_text(parser, [
#                 "#map-section > div.section-location-property.section-location-property-classified > h4 > font > font",
#                 "#ref-map",
#                 "#map-section > div.section-location-property.section-location-property-classified > h4 > font > font"
#             ])
#             logging.info(f"Location: {location}")


#             # Extract description
#             description = extract_text(parser, ["#longDescription > div", "#longDescription > div > font:nth-child(1) > font"])
#             logging.info(f"Description: {description}")

#             # Extract icon data
#             keyword_map = {
#                 'unidades': ('unidades', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 1),
#                 'total_area': ('tot', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 2),
#                 'covered_area': ('cub', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 3),
#                 'bedroom_num': ('rec', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 4),
#                 'half_bath': ('medio baño', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 5),
#                 'parking': ('estacionamientos', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 6),
#                 'bathroom_num': ('baño', "#article-container > div.development-features-grid > div > div:nth-child({}) > div.label", 7)
#             }

#             icon_data = get_icon_data(parser, keyword_map)
#             logging.info(f"Icon Data: {icon_data}")
        
            
#             # Return extracted data as a dictionary
#             return {
#                 "title": title,
#                 "status": status,
#                 "availability": availability,
#                 "price": price,
#                 "location": location,
#                 "description": description,
#                 "icon_data": icon_data
#             }
# #David: take out avisoinfo from html
# def scrape_aviso(parser, dictionary):
#     try:
#         script_tags = parser.css('script')
#         target_script = None
#         for script in script_tags:
#             if script.text() and 'const avisoInfo =' in script.text():
#                 target_script = script
#                 break
#         if target_script:
#             script_content = target_script.text()
#             dictionary = extract_aviso_info(script_content, dictionary)
#         # parse through html and find file that contains avisoInfo
#         aviso_info_match = re.search(r'const avisoInfo = ({.*?});', script_content, re.DOTALL)
#         if aviso_info_match:
#             aviso_info_str = aviso_info_match.group(1)

        
#         pattern = r'"units":\[.*\],'
#         modified_info_str = re.sub(pattern, '', aviso_info_str)
#         if aviso_info_str != modified_info_str:
#             print("This is a parent property")
#             dictionary["is_parent_property"] = True
#         else:
#             print("This is a child property")
#             dictionary["is_parent_property"] = False
#     except Exception as e:
#         print(f"An error occur occurred: {e}")
#     return dictionary


# #David: update dictionary from avisoinfo
# def scrape_data_aviso(data, dictionary):
#     dictionary = scrape_aviso(data, dictionary)
#     return dictionary

# #     regex_match = re.search(r'\{[\s\S]*?\}\s*(?=const)', aviso_info_str, re.DOTALL)
# #     content = regex_match.group(0)
# #     # Replace single quotes around keys with double quotes
# #     content = regex_handling(content)

# #     load_dictionary = json.loads(content)
# #     variables  = [
# #     "postingCode",
# #     "postingType",
# #     "price",
# #     "location",
# #     "description",
# #     "address",
# #     "whatsApp",
# #     "premier",
# #     "publisher",
# #     "realEstateType",
# #     "publicationDateFormatted",
# #     "pictures",
# #     "mainFeatures",
# #     "generalFeatures"
# # ]
# #     for variable in variables:
# #         if variable in dictionary and dictionary[variable] != None:
# #              continue
# #         elif variable in load_dictionary:
# #                 dictionary[variable] = load_dictionary[variable]
# #         else:
# #             dictionary[variable] = None

# def extract_aviso_info(script_content, data):

#     def extract_field(pattern, default=""):
#         match = re.search(pattern, script_content)
#         return match.group(1) if match else default

#     def extract_field2(pattern, default=""):
#         match = re.search(pattern, script_content)
#         if match and match.lastindex >= 2:
#             return f"{match.group(2)} {match.group(1)}"
#         elif match:
#             return match.group(1)
#         else:
#             return default

#     def extract_field3(primary_pattern, fallback_patterns, default=""):
#         # Try primary pattern
#         result = extract_field2(primary_pattern)
#         if result and result != default:
#             return result
        
#         # If primary pattern fails, try fallback patterns
#         for pattern in fallback_patterns:
#             result = extract_field2(pattern)
#             if result and result != default:
#                 return result
        
#         return default


#     # Extract key fields using regex
#     data['Title'] = extract_field(r'"title":"(.*?)"')
#     data['GeneratedTitle'] = extract_field3(r'"generatedTitle":"(.*?)"',
#                                            [r'"title":"(.*?)"'])
#     data['Description'] = extract_field(r'["\']description["\']\s*:\s*["\'](.*?)["\']')
#     data['Seller'] = extract_field(r"'name':\s*'(.*?)'")
#     data['Price'] = extract_field(r'"formattedAmount":"(.*?)"')
#     data['Publication Date'] = extract_field(r"'publicationDateFormatted':\s*'(.*?)'")
#     data['Property Dimension'] = extract_field3(
#         r'"label":"Construido","measure":"(.*?)","value":"(\d+)"',
#         [r'(\d+)\s*m²', r'(\d+)\s*sqft']
#     )
#     data['Parking Lot'] = extract_field3(
#         r'"label":"Estacionamiento","measure":null,"value":"(\d+)"',
#         [r'(\d+)\s*estacionamiento', r'(\d+)\s*parking']
#     )
#     data['Bathrooms'] = extract_field3(
#         r'"label":"[Bb]año[s]?","measure":null,"value":"(\d+)"',
#         [r'(\d+)\s*baño', r'(\d+)\s*bathroom']
#     )
#     data['Bedrooms'] = extract_field3(
#         r'"label":"Recámara","measure":null,"value":"(\d+)"',
#         [r'(\d+)\s*recámara', r'(\d+)\s*bedroom']
#     )
#     data['Age'] = extract_field(r'"label":"Antigüedad","measure":null,"value":"([\w\s]+)"')
#     data["Latitude"] = extract_field(r'"geolocation":{"latitude":([-+]?[0-9]*\.?[0-9]+)')
#     data["Longitude"] = extract_field(r'"geolocation":\{"latitude":[-+]?[0-9]*\.?[0-9]+,"longitude":([-+]?[0-9]*\.?[0-9]+)')
#     data['Pictures'] = re.findall(r'"resizeUrl1200x1200":"(.*?)"', script_content)
#     data['Property Type'] = extract_field(r'[\'"]realEstateType[\'"]:\s*\{[\'"]name[\'"]:\s*[\'"](.*?)[\'"]')
#     data['Operation Type'] = extract_field(r'"operationType":\s*\{"name":"(.*?)"')
#     data['Phone'] = extract_field(r"'partialPhone':\s*'(.*?)'")
#     data['whatsApp'] = extract_field(r'[\'"]whatsApp[\'"]:\s*[\'"](.*?)[\'"]')
#     data['Country'] = extract_field(r'"label":"PROVINCIA","depth":1,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
#     data['Zone'] = extract_field(r'"label":"ZONA","depth":3,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
#     data['City'] = extract_field(r'"label":"CIUDAD","depth":2,"parent":{"locationId":"[\w-]+","name":"(.*?)"')
#     data['Address'] = extract_field3(r'"postingLocation":{"address":{"name":"(.*?)","visibility":"EXACT"}',
#                                     [r'"address":\s*\{"name":"(.*?)"'])
#     data['postingId'] = extract_field3(r'"postingId":"(.*?)"',
#                                       [r"'idAviso':\s*'(.*?)'"])
#     data['postingCode'] = extract_field(r'[\"\']postingCode[\"\']\s*:\s*[\"\'](.*?)[\"\']')
#     data['publisherId'] = extract_field(r"'publisherId':\s*'(\d+)'")
#     data['premier'] = extract_field(r'[\"\']?premier[\"\']?\s*:\s*(true|false)')

#     # Convert lists to comma-separated strings
#     data['Pictures'] = ", ".join(data['Pictures'])
    
#     return data



