#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-12
Description:

tools.house is a tool which you can use to deal with housing searches a bit better.

TODO:
    - rentals

Updates:
    2026-01-14 06:22  - tools.house - added search with realtor/zillow, does not parse url correclty wll have to fix
    2026-01-13 06:22  - tools.house - added zillow, XPATH has been a revolution, Keys.ENTER the same way
    2026-01-13 21:07  - tools.house - added the browse mode which has been really enjoyable
    2026-01-12 01:27  - tools.house - it works!
    2026-01-11 17:06  - tools.house - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import urllib.parse
import datetime
import random
import time
import json
import csv
import re
from urllib.parse import urlparse, urljoin, unquote_plus
from typing import List, Generator, Optional, Dict, Tuple
from dataclasses import dataclass, field, asdict
from argparse import ArgumentParser

# third party imports
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
import undetected_chromedriver as uc

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath, is_file
from chriscarl.core.lib.stdlib.io import read_text_file, write_text_file
from chriscarl.core.lib.stdlib.urllib import download

SCRIPT_RELPATH = 'chriscarl/tools/house2.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

# argument defaults
DEFAULT_FIB_INIT = [0, 1]
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.house')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.house.log')

# tool constants
NOW = datetime.datetime.now().strftime('%Y-%m-%d')


def mortgage_monthly(P, apr, down=0.2, years=30, as_float=False):
    # type: (int|float, float, float, int, bool) -> int|float
    if apr > 1:
        apr /= 100
    if down > 1:
        down /= 100
    n = years * 12
    r = apr / 12
    P = P - P * down
    monthly = (P * r * (1 + r)**n) / ((1 + r)**n - 1)
    return monthly if as_float else round(monthly)


@dataclass
class Property():
    # street: str
    # city: str
    # state: str
    # zip: int
    link: str = ''
    address: str = ''
    property_type: str = ''
    price: float = 0.0
    bed: int = 1
    bath: int = 1
    hoa: float = 0.0
    land_lease: float = 0.0
    area: float = 0.0
    area_unit: str = ''
    year: int = 6969
    commute: str = ''
    listing_age: int = 0
    listing_agent: str = ''
    listing_agent_brokerage: str = ''
    monthly_30: float = 1.0
    monthly_20: float = 1.0
    monthly_15: float = 1.0
    total: float = 0.0
    per_person: float = 0.0

    # @property
    # def address(self):
    #     return f'{self.street}, {self.city}, {self.state} {self.zip}'

    def __repr__(self):
        # type: () -> str
        return f'Property({self.address!r})[{self.bed}bed/{self.bath}bath @ ${self.price:0.2f}]'

    def __str__(self):
        # type: () -> str
        return f'Property({self.address!r})'

    @staticmethod
    def parse_text(text, hostname):
        # type: (str, str) -> Property
        kwargs = {}

        if 'realtor.com' in hostname:
            regexes = [
                ('address', r'\n\s*(.+, .+, [A-Z]{2} \d{5})', re.MULTILINE),
                ('property_type', r'Property type\n(.+)\n', re.MULTILINE),
                ('price', r'\n\s*\$([\d,]{5,})', re.MULTILINE),
                ('bed', r'([\d]+)\n\s*bed', re.MULTILINE),
                ('bath', r'([\d]+)\n\s*bath', re.MULTILINE),
                ('hoa', r'HOA fees\n\$?([\d\.,]{3,})', re.MULTILINE),
                ('land_lease', r'(?:land lease|rent)[^\d]+\$?([\d\., ]{3,})[^\d]', re.IGNORECASE | re.MULTILINE),
                ('area', r'([\d\.,]{3,}) (square foot lot|acre lot|square feet)', re.MULTILINE),
                ('area_unit', r'[\d\.,]{3,} (square foot lot|acre lot|square feet)', re.MULTILINE),
                ('year', r'Year built\n(.+)', re.MULTILINE),
                ('commute', r'(\d+ min)\nto', re.MULTILINE),
                ('listing_age', r'On Realtor.com\n(\d+) days', re.MULTILINE),
                ('listing_agent', r'Listed by (.+)', 0),
                ('listing_agent_brokerage', r'Brokered by (.+)', 0),
            ]
        elif 'zillow.com' in hostname:
            regexes = [
                ('address', r'\n\s*(.+, .+, [A-Z]{2} \d{5})', re.MULTILINE),
                ('property_type', r'Home type\:\s*(.+)\n', re.MULTILINE),
                ('price', r'\n\s*\$([\d,]{5,})', re.MULTILINE),
                ('bed', r'([\d]+)\s*bed', re.MULTILINE),
                ('bath', r'([\d]+)\s*bath', re.MULTILINE),
                ('hoa', r'\$?([\d\.,]{3,})\/mo HOA', 0),
                ('land_lease', r'(?:lease amount|rent)\:+s*\$?([\d\., ]{3,})', re.IGNORECASE),
                ('area', r'area\:\s*([\d\.,]{3,})', re.MULTILINE),
                ('area_unit', r'area\:\s*([\d\.,]{3,}) (sqft lot|acre lot|sqft)', re.MULTILINE),
                ('year', r'Year built\:\s*(.+)', re.MULTILINE),
                ('commute', r'(\d+ min)\nto', re.MULTILINE),
                ('listing_age', r'(\d+) days on Zillow', re.MULTILINE),
                ('listing_agent', r'Listed by:\n([^\d]+)\s+[\d \-]+,\n(?:.+)\s+[\d\-\(\)]{9,}', re.MULTILINE),
                ('listing_agent_brokerage', r'Listed by:\n(?:[^\d]+)\s+[\d \-]+,\n(.+)\s+[\d\-\(\)]{9,}', re.MULTILINE),
            ]
        else:
            raise NotImplementedError(f'{hostname} not yet implemented!')

        for tpl in regexes:
            key, regex, flags = tpl
            try:
                default = getattr(DEFAULT_PROPERTY, key)
                KeyType = type(default)
                mo = re.search(regex, text, flags=flags)
                if not mo:
                    # LOGGER.debug(text)
                    value = '' if KeyType is str else default
                    # raise RuntimeError(f'could not find {key!r} in realtor.com text!')
                else:
                    value = mo.groups()[0]

                if KeyType in (int, float) and isinstance(value, str):
                    value = re.sub(r'[ ,]', '', value)

                value = KeyType(value)
                kwargs[key] = value
            except Exception:
                LOGGER.error('failed to parse %d with regex "%s"!', key, regex)
                LOGGER.debug('failed to parse %d with regex "%s"!', key, regex, exc_info=True)
                continue

        prop = Property(**kwargs)
        return prop

    def calculate(self, APR_15=6.1, APR_20=6.5, APR_30=6.9, down=20.0):
        # type: (float, float, float, float) -> None
        self.monthly_15 = mortgage_monthly(self.price, APR_15, down=down, years=15)
        self.monthly_20 = mortgage_monthly(self.price, APR_20, down=down, years=20)
        self.monthly_30 = mortgage_monthly(self.price, APR_30, down=down, years=30)
        self.total = self.monthly_30 + self.hoa + self.land_lease
        self.per_person = self.total / self.bed

    def to_dict(self):
        return asdict(self)


URL_MORTGAGE_RATES = 'https://datawrapper.dwcdn.net/cHKhW/56/dataset.csv'


def download_mortgage_rates(dirpath=TEMP_DIRPATH):
    # type: (str) -> Tuple[float, float, float]
    '''
    Description:
        URL used: https://datawrapper.dwcdn.net/cHKhW/56/dataset.csv

        other urls:
            # https://www.forbes.com/advisor/mortgages/current-20-year-mortgages-rates/
            # https://widgets.icanbuy.com/js/median_home_price_by_zip.js
            # https://widgets.icanbuy.com/js/zipCodeRangeByState.js
            # https://datawrapper.dwcdn.net/cHKhW/56/dataset.csv <- contains the actual data

    Returns:
        Tuple[float, float, float]
            30yr, 20yr, 15yr
    '''
    dataset_filepath, _ = download(URL_MORTGAGE_RATES, dirpath)
    with open(dataset_filepath, 'r', encoding='utf-8') as r:
        reader = csv.DictReader(r, delimiter=';')
        datas = list(reader)

    mortgage_rate_30 = 0.0
    mortgage_rate_20 = 0.0
    mortgage_rate_15 = 0.0
    for data in datas:
        if data['Loan Term'] == '30-Year Fixed':
            mortgage_rate_30 = float(data['Interest Rate'])
        elif data['Loan Term'] == '20-Year Fixed':
            mortgage_rate_20 = float(data['Interest Rate'])
        elif data['Loan Term'] == '15-Year Fixed':
            mortgage_rate_15 = float(data['Interest Rate'])

    return mortgage_rate_30, mortgage_rate_20, mortgage_rate_15


DEFAULT_PROPERTY = Property()


def realtor_com_populate_commute(driver, wait, url, commute_address):
    # type: (WebDriver, WebDriverWait, str, str) -> bool
    LOGGER.debug('looking for the commute button')
    if driver.current_url != url:
        driver.get(url)

    wait.until(EC.presence_of_element_located((By.ID, 'Property details')))
    the_button = None
    for button in driver.find_elements(By.TAG_NAME, 'button'):
        attrib = button.get_attribute('data-testid')
        if attrib == 'ldp-commute-time-btn' and isinstance(button.text, str):
            if 'add a commute' in button.text.lower():
                the_button = button
                break

    if the_button:
        LOGGER.debug('inputting the commute %r', commute_address)
        the_button.click()
        modal = wait.until(EC.presence_of_element_located((By.ID, 'ldp-commute-time-modal')))
        input = modal.find_element(By.ID, 'searchbox-input')
        for token in commute_address.split(',')[:-1]:
            for char in token:
                input.send_keys(char)
                # time.sleep(0.1) # DO NOT SLEEP, the query box will come up and get confused if you do
            input.send_keys(',')

        LOGGER.debug('sending keys down and enter')
        time.sleep(3)
        input.send_keys(Keys.DOWN)
        time.sleep(0.5)
        input.send_keys(Keys.ENTER)

        LOGGER.debug('looking for the confirm button')
        time.sleep(3)
        the_button = None
        for button in driver.find_elements(By.TAG_NAME, 'button'):
            attrib = button.get_attribute('data-testid')
            if attrib == 'update-commute-button' and isinstance(button.text, str):
                if 'add commute' in button.text.lower():
                    the_button = button
                    break
        if the_button:
            the_button.click()

        time.sleep(5)

    return True


def realtor_com_to_text(driver, wait, url, sleep_for=3):
    # type: (WebDriver, WebDriverWait, str, int|float) -> str
    # data = {}
    text = []

    LOGGER.debug('%s - expanding property details', url)
    if driver.current_url != url:
        driver.get(url)

    ele = wait.until(EC.presence_of_element_located((By.ID, 'Property details')))
    for button in ele.find_elements(By.TAG_NAME, 'button'):
        if isinstance(button.text, str) and 'show more' in button.text.lower():
            button.click()
    # time.sleep(1)
    # ele = driver.find_element(By.ID, 'Property details')
    # for button in ele.find_elements(By.TAG_NAME, 'button'):
    #     if isinstance(button.text, str) and 'show more' in button.text.lower():
    #         button.click()

    details = driver.find_element(By.ID, 'Property details')
    details_text = str(details.text)
    data_testids = [
        'for-sale',
        'ldp-agent-overview',
        'ldp-list-price',
        'ldp-home-facts',
        'ldp-highlighted-facts',
        'ldp-commute-time',
    ]
    for data_testid in data_testids:
        div = driver.find_element(By.XPATH, f'//*[@data-testid="{data_testid}"]')
        text.append(div.text)

    # data['details'] = details_text
    text.append(details_text)
    time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)

    return '\n'.join(text)


def zillow_com_to_text(driver, wait, url, sleep_for=3, captcha_timeout=25):
    # type: (WebDriver, WebDriverWait, str, int|float, int|float) -> str
    text = []

    LOGGER.debug('%s - expanding property details', url)
    if driver.current_url != url:
        driver.get(url)

    # wait.until(EC.presence_of_element_located((By.XPATH, f'//section[@data-testid="contact-form"]')))
    # wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="hidden-reg-details"]')))
    # wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="bdp-building-location"]')))
    div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'layout-static-column-container')))

    try:
        if driver.find_element(By.ID, 'px-captcha-modal'):
            LOGGER.warning('must solve captcha!')
            now = time.time()
            while driver.find_element(By.ID, 'px-captcha-modal'):
                LOGGER.warning('must solve captcha!')
                time.sleep(1)
                if time.time() - now > captcha_timeout:
                    raise RuntimeError('failed captcha timeout!')

            div = driver.find_element(By.CLASS_NAME, 'layout-static-column-container')
    except NoSuchElementException:
        pass

    body = wait.until(EC.presence_of_element_located((By.XPATH, f'//body')))
    for _ in range(5):
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)
    for _ in range(5):
        body.send_keys(Keys.PAGE_UP)
        time.sleep(0.2)

    buttons = [
        'description',
        'facts-and-features-wrapper-footer',
    ]
    while buttons:
        section = buttons.pop(0)
        div = driver.find_element(By.XPATH, f'//div[@data-testid="{section}"]')
        button = div.find_element(By.TAG_NAME, 'button')
        button.send_keys(Keys.ENTER)  # NOTE: instead of .click()
        time.sleep(0.5)

    div = driver.find_element(By.CLASS_NAME, 'layout-static-column-container')
    dts = div.find_elements(By.TAG_NAME, 'dt')
    dt_text = ' '.join([str(dt.text) for dt in dts])
    text.append(dt_text)

    data_testids = [
        'home-details-chip-container',
        'description',
        'facts-and-features-module',
        'seller-attribution',
    ]
    aria_labels = [
        'At a glance facts',
    ]
    for data_testid in data_testids:
        div = driver.find_element(By.XPATH, f'//div[@data-testid="{data_testid}"]')
        text.append(div.text)
    for aria_label in aria_labels:
        div = driver.find_element(By.XPATH, f'//div[@aria-label="{aria_label}"]')
        text.append(div.text)

    time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)

    return '\n'.join(text)


def realtor_com_search_page_visit(driver, wait, url):
    # type: (WebDriver, WebDriverWait, str) -> List[str]
    # url = 'https://www.realtor.com/realestateandhomes-search/San-Jose_CA'
    if driver.current_url != url:
        driver.get(url)
    LOGGER.debug('scrapping page %s', url)
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-testid="card-content"]//a')))
    body = driver.find_element(By.XPATH, '//body')  # still exists
    while True:
        try:
            # no matches found
            driver.find_element(By.XPATH, '//p[contains(normalize-space(.), "nd of matching")]')
            break
        except NoSuchElementException:
            pass

        try:
            # paginator found
            driver.find_element(By.XPATH, '//div[@aria-label="pagination"]')
            break
        except NoSuchElementException:
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.1)

    urls = []
    for anchor in driver.find_elements(By.XPATH, '//div[@data-testid="card-content"]//a'):
        href = anchor.get_attribute('href')
        if not href:
            continue
        else:
            urls.append(urljoin(url, href))

    return urls


def realtor_com_search(
    driver,
    wait,
    city=None,
    state=None,
    zip=None,
    price_max=None,
    price_min=None,
    show_contingent=False,
    sleep_for=3,
):
    # type: (WebDriver, WebDriverWait, Optional[str], Optional[str], Optional[int], Optional[int|float], Optional[int|float], bool, int|float) -> List[str]
    if not ((city and state) or (zip)):
        raise ValueError('must provide either city and state OR zip!')

    # searching manually:
    # url = 'https://www.realtor.com'
    # driver.get(url)
    # search = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    # # search = driver.find_element(By.XPATH, '//input[@type="text"]')
    # if (city and state):
    #     # search.send_keys('San Jose, CA')
    #     search.send_keys(f'{city}, {state}')
    # else:
    #     search.send_keys(f'{zip}')
    # time.sleep(1)
    # search.send_keys(Keys.DOWN)
    # time.sleep(0.1)
    # search.send_keys(Keys.ENTER)

    # searching via heuristic, tokens are done via route additions rather than params... weird AF
    tokens = ['https://www.realtor.com/realestateandhomes-search']
    if (city and state):
        # San-Jose_CA
        tokens.append(f'{"-".join(city.split())}_{state}')
    else:
        # 10001
        tokens.append(f'{zip}')
    if price_max is not None or price_min is not None:
        # price-na-400000
        tokens.append(f'price-{"na" if price_min is None else int(price_min)}-{"na" if price_max is None else int(price_max)}')
    if not show_contingent:
        tokens.append('pnd-ctg-hide')

    # TODO: property types: everything after type- is valid and csv... weird AF
    # type-multi-family-home,townhome,condo,mfd-mobile-home,land,farms-ranches,single-family-home
    # https://www.realtor.com/realestateandhomes-search/San-Jose_CA/pnd-ctg-hide/price-na-400000
    search_url = f'{"/".join(tokens)}/'
    LOGGER.info('%s', search_url)
    urls = realtor_com_search_page_visit(driver, wait, search_url)  # page 1
    LOGGER.info('scraped page 1, %d urls discovered so far', len(urls))

    # see if htere is a page 2
    try:
        # no matches found
        driver.find_element(By.XPATH, '//p[contains(normalize-space(.), "nd of matching")]')
        return urls
    except NoSuchElementException:
        pass

    # paginator found
    pages = driver.find_element(By.XPATH, '//div[@aria-label="pagination"]')
    max_page_mo = re.search(r'(\d+)\nnext', pages.text, flags=re.MULTILINE | re.IGNORECASE)
    if not max_page_mo:
        raise RuntimeError('could not find the max page for the search!')
    max_page = int(max_page_mo.groups()[0])
    if max_page > 1:
        base = urlparse(driver.current_url)
        base_url = f'{base.scheme}://{base.hostname}{base.path}/'
        for page in range(2, max_page + 1):
            LOGGER.info('scrapping %d / %d, %d urls discovered so far', page, max_page, len(urls))
            # https://www.realtor.com/realestateandhomes-search/San-Jose_CA/pg-2
            # https://www.realtor.com/realestateandhomes-search/San-Jose_CA/pg-3...
            search_url_page = urljoin(base_url, f'pg-{page}')
            urls.extend(realtor_com_search_page_visit(driver, wait, search_url_page))
            time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)

    LOGGER.info('found %d urls', len(urls))
    return urls


def zillow_com_search_page_visit(driver, wait):
    # type: (WebDriver, WebDriverWait) -> List[str]

    # this div IS interactable, others arent..
    grid = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="search-page-list-container"]')))
    for _ in range(10):
        grid.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.1)

    urls = []
    for anchor in driver.find_elements(By.XPATH, '//div[@data-testid="property-card-data"]/a'):
        href = anchor.get_attribute('href')
        if not href:
            continue
        else:
            urls.append(href)

    return urls


def zillow_com_search(
    driver,
    wait,
    city=None,
    state=None,
    zip=None,
    price_max=None,
    price_min=None,
    show_contingent=False,
    sleep_for=3,
):
    # type: (WebDriver, WebDriverWait, Optional[str], Optional[str], Optional[int], Optional[int|float], Optional[int|float], bool, int|float) -> List[str]
    if not ((city and state) or (zip)):
        raise ValueError('must provide either city and state OR zip!')

    driver.get('https://zillow.com')
    inp = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-testid="search-bar-container"]//input')))

    LOGGER.debug('applying the search')
    if (city and state):
        inp.send_keys(f'{city}, {state}')
    else:
        inp.send_keys(str(zip))
    time.sleep(1)
    inp.send_keys(Keys.ENTER)
    time.sleep(1)

    # potentially loads a modal...
    try:
        # TODO: rent as well...
        for_sale_button = driver.find_element(By.XPATH, '//div[@aria-label="Choose listing type"]//button')
        LOGGER.debug('for sale/rent modal found')
        for_sale_button.click()
    except NoSuchElementException:
        pass

    # new page loads up
    # wait for the grid
    LOGGER.debug('attempting to retrieve query dict')
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="search-page-list-container"]')))

    # the complex params pop up after switching sort mechanism so lets do that
    sort_button = driver.find_element(By.XPATH, '//button[@data-test="sort-popover-dropdown-button"]')
    sort_button.click()  # new buttons populate
    time.sleep(0.2)
    newest_button = driver.find_element(By.XPATH, '//button[@data-value="days"]')
    newest_button.click()
    time.sleep(0.2)

    # new page loads
    # wait for the grid
    LOGGER.debug('modifying query dict')
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="search-page-list-container"]')))

    # get and modify the params dict
    url = unquote_plus(driver.current_url)
    parsed = urlparse(url)

    query, dick_params = parsed.query.split('=')
    data = json.loads(dick_params)
    if 'price' not in data['filterState'] and (price_max or price_min):
        data['filterState']['price'] = dict(min=0, max=0)

    # apply the filter params
    data['filterState']['price']['max'] = price_max or 10000000
    data['filterState']['price']['min'] = price_min or 0
    data['filterState']['pnd'] = {'value': show_contingent}

    minified = re.sub(r'(\s{2,}|\n)', '', json.dumps(data))
    minified = re.sub(r'([\:,]) ', r'\g<1>', minified)

    search_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}?{query}={minified}'
    LOGGER.debug('modified the search url from %s to %s', url, search_url)
    driver.get(search_url)

    try:
        pagination = driver.find_element(By.XPATH, '//div[@data-testid="search-pagination"]')
        pages = re.findall(r'\d+', pagination.text)
        max_page = int(pages[-1])
    except NoSuchElementException:
        max_page = 1
    LOGGER.info('%d pages to search through!', max_page)
    page = 1

    urls = zillow_com_search_page_visit(driver, wait)  # visit the current page
    LOGGER.info('scraped page %d, %d urls discovered so far', page, len(urls))

    while True:
        try:
            next_arrow = driver.find_element(By.XPATH, '//div[@data-testid="search-pagination"]//a[@rel="next"]')
            aria_disabled = next_arrow.get_attribute('aria-disabled')
            if aria_disabled and aria_disabled == 'true':
                break
        except NoSuchElementException:
            break
        page += 1

        LOGGER.info('scrapping %d / %d, %d urls discovered so far', page, max_page, len(urls))
        next_arrow.click()
        new_urls = zillow_com_search_page_visit(driver, wait)
        urls.extend(new_urls)
        time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)

    LOGGER.info('found %d urls', len(urls))
    return urls


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    mode: str = ''
    input_filepath: str = ''
    commute: str = ''
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH

    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[int] = None
    price_max: Optional[int | float] = None
    price_min: Optional[int | float] = None
    show_contingent: bool = False

    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def add_common_arguments(parser):
        parser.add_argument('--commute', '-c', type=str, help='an address youd like to calculate a commute from')
        parser.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to save the output json and downloaded descriptions')

        parser.add_argument('--debug', action='store_true', help='chose to print debug info')
        parser.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        parser.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        modes = parser.add_subparsers(title='mode', description='pick one of the modes')

        url_file = modes.add_parser('url-file', help='one-shot through a list of urls granted via file')
        Arguments.add_common_arguments(url_file)
        url_file.set_defaults(mode='url-file')
        url_file.add_argument('input_filepath', type=str, help='filepath with urls to injest')

        browse = modes.add_parser('browse', help='open up a driver and browse at our liesure until closed')
        Arguments.add_common_arguments(browse)
        browse.set_defaults(mode='browse')

        search = modes.add_parser('search', help='run a search query on all websites and collate')
        Arguments.add_common_arguments(search)
        search.set_defaults(mode='search')
        search.add_argument('--city', type=str, help='full name of a city like "San Jose"')
        search.add_argument('--state', type=str, help='acronym state like "CA"')
        search.add_argument('--zip', type=int, help='5-digit ZIP code like 10001')
        search.add_argument('--price-max', type=int, help='some maximum price?')
        search.add_argument('--price-min', type=int, help='some minimum price?')
        search.add_argument('--show-contingent', action='store_true', help='show pending or contingent?')

        return parser

    def process(self):
        if self.mode == 'search':
            if not ((self.city and self.state) or (self.zip)):
                raise RuntimeError('must provide either --city + --state OR --zip!')
        make_dirpath(self.output_dirpath)
        if self.debug:
            self.log_level = 'DEBUG'
        configure_ez(level=self.log_level, filepath=self.log_filepath)

    @staticmethod
    def parse(parser=None, argv=None):
        # type: (Optional[ArgumentParser], Optional[List[str]]) -> Arguments
        parser = parser or Arguments.argparser()
        ns = parser.parse_args(argv)
        arguments = Arguments(**(vars(ns)))
        arguments.process()
        return arguments


def url_file(input_filepath, output_dirpath, commute='', driver=None, wait=None):
    # type: (str, str, str, Optional[WebDriver], Optional[WebDriverWait]) -> None
    url_text = read_text_file(input_filepath)
    urls = [url.strip() for url in url_text.splitlines() if url.strip() and not url.strip().startswith('#')]
    filename = os.path.splitext(os.path.basename(input_filepath))[1]

    # NOTE: use_subprocess=False in python interactive mode
    driver = driver or uc.Chrome(headless=False, use_subprocess=True)
    wait = wait or WebDriverWait(driver, 5)

    cache_dirpath = abspath(output_dirpath)
    os.makedirs(cache_dirpath, exist_ok=True)

    LOGGER.info('downloading mortgage rates')
    mortgage_rate_30, mortgage_rate_20, mortgage_rate_15 = download_mortgage_rates(dirpath=output_dirpath)
    LOGGER.info('30 Year mortgage rate of %0.2f%%', mortgage_rate_30)

    if commute:
        realtor_com_populate_commute(driver, wait, urls[-1], commute)

    LOGGER.info('url processing')
    properties = []
    for u, url in enumerate(urls):
        if 'rentals' in url:
            LOGGER.error('%d / %d - NotImplementedError for a url like %s!', u + 1, len(urls), url)
            continue

        parsed = urllib.parse.urlparse(url)
        cache_filename = f'{u}'
        hostname = str(parsed.hostname) if parsed.hostname else ''
        if hostname:
            cache_filename = parsed.path.split('/')[-1]
        cached_filepath = abspath(cache_dirpath, f'{cache_filename}.txt')
        if is_file(cached_filepath):
            LOGGER.info('%d / %d - from file:    %s', u + 1, len(urls), url)
            text = read_text_file(cached_filepath)
        else:
            LOGGER.info('%d / %d - from browser: %s', u + 1, len(urls), url)
            if 'realtor.com' in hostname:
                text = realtor_com_to_text(driver, wait, url)
            elif 'zillow.com' in hostname:
                text = zillow_com_to_text(driver, wait, url)
            else:
                raise NotImplementedError(f'not implemented for {hostname!r}!')
            write_text_file(cached_filepath, f'{url}\n{text}')

        prop = Property.parse_text(text, hostname=hostname)
        prop.link = url
        prop.calculate(mortgage_rate_15, mortgage_rate_20, mortgage_rate_30)
        properties.append(prop)

    property_dicts = [asdict(prop) for prop in properties]
    LOGGER.info('found %d properties', len(property_dicts))
    if property_dicts:
        output_filepath_json = abspath(output_dirpath, f'{filename}.json')
        if os.path.isfile(output_filepath_json):
            with open(output_filepath_json, 'r', encoding='utf-8') as r:
                existing_dicts = json.load(r)
            property_dicts.extend(existing_dicts)

        keys = list(asdict(DEFAULT_PROPERTY).keys())
        output_filepath_csv = abspath(output_dirpath, f'{filename}.csv')
        with open(output_filepath_csv, 'w', encoding='utf-8', newline='') as w:
            writer = csv.DictWriter(w, fieldnames=keys)
            writer.writeheader()
            writer.writerows(property_dicts)
        LOGGER.info('wrote "%s"', output_filepath_csv)

        with open(output_filepath_json, 'w', encoding='utf-8') as w:
            json.dump(property_dicts, w, indent=2)
        LOGGER.info('wrote "%s"', output_filepath_json)


def get_url(driver):
    # type: (WebDriver) -> str|None
    try:
        return urllib.parse.unquote_plus(driver.current_url.strip())
    except Exception:
        LOGGER.warning('driver is likely dead')
        return None


def browse(output_dirpath, commute='', driver=None, wait=None):
    # type: (str, str, Optional[WebDriver], Optional[WebDriverWait]) -> None
    # NOTE: use_subprocess=False in python interactive mode

    driver = driver or uc.Chrome(headless=False, use_subprocess=True)
    wait = wait or WebDriverWait(driver, 20)  # in case you need to resolve a captcha or something

    cache_dirpath = abspath(output_dirpath)
    os.makedirs(cache_dirpath, exist_ok=True)

    LOGGER.info('downloading mortgage rates')
    mortgage_rate_30, mortgage_rate_20, mortgage_rate_15 = download_mortgage_rates(dirpath=output_dirpath)
    LOGGER.info('30 Year mortgage rate of %0.2f%%', mortgage_rate_30)

    properties = []
    u = 0
    commute_dealt_with = False
    url = ''
    driver_url = get_url(driver)
    try:
        while driver_url is not None:
            if url == driver_url:
                time.sleep(0.2)
                driver_url = get_url(driver)
                continue

            url = driver_url
            if 'rentals' in url:
                LOGGER.error('NotImplementedError for a url like %s!', url)
                continue

            parsed = urllib.parse.urlparse(url)
            if not parsed.path:
                continue

            u += 1

            cache_filename = f'{u}'
            hostname = str(parsed.hostname) if parsed.hostname else ''
            if hostname:
                cache_filename = parsed.path.split('/')[-1]
            cached_filepath = abspath(cache_dirpath, f'{cache_filename}.txt')
            if is_file(cached_filepath):
                LOGGER.info('%d - %s from file', u + 1, url)
                text = read_text_file(cached_filepath)
            else:
                LOGGER.info('%d - %s from browser', u + 1, url)
                if 'realtor.com' in hostname and 'realestateandhomes-detail' in parsed.path:
                    if commute and not commute_dealt_with:
                        realtor_com_populate_commute(driver, wait, url, commute)
                        commute_dealt_with = True
                    text = realtor_com_to_text(driver, wait, url)
                elif 'zillow.com' in hostname and 'homedetails' in parsed.path:
                    text = zillow_com_to_text(driver, wait, url)
                else:
                    LOGGER.debug('not implemented for hostname %r', hostname)
                    continue
                    # raise NotImplementedError(f'not implemented for {hostname!r}!')
                write_text_file(cached_filepath, f'{url}\n{text}')

                prop = Property.parse_text(text, hostname=hostname)
                prop.link = url
                prop.calculate(mortgage_rate_15, mortgage_rate_20, mortgage_rate_30)
                LOGGER.info('discovered property: %s', prop)
                properties.append(prop)

            driver_url = get_url(driver)
    except KeyboardInterrupt:
        driver.close()
        LOGGER.warning('ctrl + c detected!')

    property_dicts = [asdict(prop) for prop in properties]
    LOGGER.info('found %d properties', len(property_dicts))
    if property_dicts:
        output_filepath_json = abspath(output_dirpath, f'{NOW}.json')
        if os.path.isfile(output_filepath_json):
            with open(output_filepath_json, 'r', encoding='utf-8') as r:
                existing_dicts = json.load(r)
            property_dicts.extend(existing_dicts)

        keys = list(asdict(DEFAULT_PROPERTY).keys())
        output_filepath_csv = abspath(output_dirpath, f'{NOW}.csv')
        with open(output_filepath_csv, 'w', encoding='utf-8', newline='') as w:
            writer = csv.DictWriter(w, fieldnames=keys)
            writer.writeheader()
            writer.writerows(property_dicts)
        LOGGER.info('wrote "%s"', output_filepath_csv)

        with open(output_filepath_json, 'w', encoding='utf-8') as w:
            json.dump(property_dicts, w, indent=2)
        LOGGER.info('wrote "%s"', output_filepath_json)


def search(output_dirpath, city=None, state=None, zip=None, price_max=None, price_min=None, show_contingent=False, commute='', driver=None, wait=None):
    # type: (str, Optional[str], Optional[str], Optional[int], Optional[int | float], Optional[int | float], bool, str, Optional[WebDriver], Optional[WebDriverWait]) -> None

    # NOTE: use_subprocess=False in python interactive mode
    driver = driver or uc.Chrome(headless=False, use_subprocess=True)
    wait = wait or WebDriverWait(driver, 20)  # in case you need to resolve a captcha or something

    cache_dirpath = abspath(output_dirpath)
    os.makedirs(cache_dirpath, exist_ok=True)

    search_args = (driver, wait)
    search_kwargs = dict(city=city, state=state, zip=zip, price_max=price_max, price_min=price_min, show_contingent=show_contingent)
    zillow_com_urls = zillow_com_search(*search_args, **search_kwargs)
    realtor_com_urls = realtor_com_search(*search_args, **search_kwargs)
    urls = realtor_com_urls + zillow_com_urls
    if urls:
        output_filepath_urls = abspath(output_dirpath, f'{NOW}.urls')
        write_text_file(output_filepath_urls, '\n'.join(urls))
        LOGGER.info('wrote "%s"', output_filepath_urls)

        url_file(output_filepath_urls, output_dirpath, commute=commute, driver=driver, wait=wait)


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    if args.mode == 'url-file':
        url_file(args.input_filepath, args.output_dirpath, commute=args.commute)
    elif args.mode == 'browse':
        browse(args.output_dirpath, commute=args.commute)
    elif args.mode == 'search':
        search(
            args.output_dirpath,
            city=args.city,
            state=args.state,
            zip=args.zip,
            price_max=args.price_max,
            price_min=args.price_min,
            show_contingent=args.show_contingent,
            commute=args.commute,
        )

    LOGGER.info('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
