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
url = 'https://www.inmuebles24.com/propiedades/clasificado/alclapin-departamento-juarez-143611198.html'

# goes to specific url and gets aviosinfo

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(browser_url)
        # browser = await option.new_context()
        print('Successfully Connected')

        page = await browser.new_page()
        print('Successfully Opened webpage')
        await page.goto(url, timeout=300000)
        const = 5000
        await page.wait_for_timeout(const)
        print(f"Waited for additional {const // 1000} seconds")
        page_content =  await page.content()


        # Parse the html file and find avisInfo
        parser = HTMLParser(page_content)
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
            try:
                with open('sample_website.json', 'w') as file:
                    file.write(aviso_info_str)
                print("File written successfully.")
            except Exception as e:
                print(f"An error occurred: {e}")

asyncio.run(main())