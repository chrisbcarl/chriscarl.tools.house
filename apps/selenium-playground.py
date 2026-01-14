'''
Author:      Chris Carl
Date:        2024-11-11
Email:       chrisbcarl@outlook.com

Description:
    run this code to get a python environment loaded that'll let you explore worshiping olympus


Updated:
    2026-01-14 - selenium-playground - some extra tips n tricks added like undetected_chromedriver, not foolproof
    2024-11-21 - selenium-playground - pypa refactor
    2024-11-13 - selenium-playground - extra playful things like moving most reusable stuff to hellenist_lib and reloading it here
    2024-11-11 - selenium-playground - initial commit
'''
import os
import re
import json
import time
import random
import datetime
import logging
import subprocess
from dataclasses import asdict
from urllib.parse import urlparse, unquote, unquote_plus, urljoin
from typing import Any, List, Dict, Callable, Generator

# third party
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

LOGGER = logging.getLogger('root')

logging.basicConfig(format='%(asctime)s - %(levelname)8s - %(funcName)16s: %(message)s', level='INFO', force=True)

DEFAULT_CHROME_DEBUG_PORT = 7654
NOW = datetime.datetime.now()
try:
    SCRIPT_DIRPATH = os.path.abspath(os.path.dirname(__file__))
except Exception:
    SCRIPT_DIRPATH = os.getcwd()
OUTPUT_DIRPATH = os.path.join(SCRIPT_DIRPATH, 'ignoreme/downloads', NOW.strftime('%Y-%m-%d'))
if not os.path.isdir(OUTPUT_DIRPATH):
    os.makedirs(OUTPUT_DIRPATH)


def get_uri_host(uri):
    '''https://stackoverflow.com/a/9626596'''
    parsed_uri = urlparse(uri)
    result = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
    return result


ITERATION = 0


def save_page(driver):
    # type: (WebDriver) -> None
    global ITERATION
    current_uri = driver.current_url
    uri = current_uri.split('?')[0]
    host = get_uri_host(uri)
    components = uri.replace(host, '').split('/')
    output_dir = os.path.join(OUTPUT_DIRPATH, str(ITERATION))
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    component = ''
    for comp in reversed(components):
        if comp:
            component = comp
            break
    logging.info('saving %d - %s to "%s"', ITERATION, uri, output_dir)

    cookies = driver.get_cookies()
    with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as w:
        json.dump(dict(current_uri=current_uri, uri=uri, host=host, components=components, iteration=ITERATION, cookies=cookies), w, indent=2)

    with open(os.path.join(output_dir, f'{component}.html'), 'w', encoding='utf-8') as w:
        w.write(driver.page_source)

    with open(os.path.join(output_dir, f'{component}.cookies'), 'w', encoding='utf-8') as w:
        json.dump(cookies, w, indent=4)

    cookie_str = '; '.join(f'{cookie["name"]}={cookie["value"]}' for cookie in cookies)
    with open(os.path.join(output_dir, f'{component}.cookiestr'), 'w', encoding='utf-8') as w:
        w.write(cookie_str)

    driver.save_screenshot(os.path.join(output_dir, f'{component}.png'))

    ITERATION += 1


options = webdriver.EdgeOptions()
# options.add_argument(f"user-data-dir={os.path.expanduser(r'~\AppData\Local\Microsoft\Edge\User Data\Default')}") # edge://version
# https://stackoverflow.com/questions/6509628/how-to-get-http-response-code-using-selenium-webdriver/50932205#50932205
options.add_argument(f'--remote-debugging-port={DEFAULT_CHROME_DEBUG_PORT}')
options.add_argument('--remote-allow-origins=*')
prefs = {}
# prefs['profile.default_content_settings.popups'] = 0
prefs['download.default_directory'] = os.path.expanduser(OUTPUT_DIRPATH)
options.add_experimental_option('prefs', prefs)

serv = Service(popen_kw={'creation_flags': subprocess.CREATE_NEW_PROCESS_GROUP})  # prevent ctrl + c
driver = webdriver.ChromiumEdge(options=options, service=serv)
driver.get('https://www.google.com')
driver.implicitly_wait(3)

save_page(driver)

# to deal with some CloudFlare and captcha'd stuff
# NOTE: use_subprocess=False in python interactive mode
driver = uc.Chrome(headless=False, use_subprocess=False)
wait = WebDriverWait(driver, 20)

# typical find one element via xpath, real powerful stuff
inp = wait.until(EC.presence_of_element_located((By.XPATH, '//section[@type="main"]//input')))

sleep_for = 3
time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)
