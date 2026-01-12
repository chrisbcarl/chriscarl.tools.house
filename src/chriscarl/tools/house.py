#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-12
Description:

tools.house2 is a tool which... TODO: lorem ipsum

Updates:
    2026-01-12 - tools.house2 - initial commit
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import random
import time
import json
import csv
import re
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



def mortgage_monthly(P, apr, down=0.2, years=30, as_float=False):
    # type: (int|float, float, float, int, bool) -> int|float
    if apr > 1:
        apr /= 100
    if down > 1:
        down /= 100
    n = years * 12
    r = apr / 12
    P = P - P * down
    monthly = (P * r * (1+r)**n) / ((1+r)**n - 1)
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

    @staticmethod
    def parse_realtor_com(text):
        # type: (str) -> Property
        kwargs = {}

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
        for tpl in regexes:
            try:
                key, regex, flags = tpl
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

def realtor_com_populate_commute(driver, wait, url, commute_address):
    # type: (WebDriver, WebDriverWait, str, str) -> bool
    LOGGER.debug('looking for the commute button')

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

    driver.get(url)
    ele = wait.until(EC.presence_of_element_located((By.ID, 'Property details')))
    for button in ele.find_elements(By.TAG_NAME, 'button'):
        if isinstance(button.text, str) and 'show more' in button.text.lower():
            button.click()

    details = driver.find_element(By.ID, 'Property details')
    wanted = ['for-sale', 'ldp-agent-overview', 'ldp-list-price', 'ldp-home-facts', 'ldp-highlighted-facts', 'ldp-commute-time']
    for div in driver.find_elements(By.TAG_NAME, 'div'):
        try:
            attrib = div.get_attribute('data-testid')
            if not attrib:
                continue
            elif attrib in wanted:
                # data[attrib] = div.text
                text.append(div.text)
        except Exception:
            pass

    # data['details'] = details.text
    text.append(details.text)
    time.sleep(random.randint(0, int(1000 * sleep_for)) / 1000)

    return '\n'.join(text)


DEFAULT_PROPERTY = Property()


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    input_filepath: str
    commute: str = ''
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('input-filepath', type=str, help='filepath with urls to injest')
        app.add_argument('--commute', '-c', type=str, help='an address youd like to calculate a commute from')
        app.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to save the output json and downloaded descriptions')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
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


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    os.makedirs(args.output_dirpath, exist_ok=True)

    url_text = read_text_file(args.input_filepath)
    urls = [url.strip() for url in url_text.splitlines() if url.strip() and not url.strip().startswith('#')]
    filename = os.path.splitext(os.path.basename(args.input_filepath))[1]

    # NOTE: use_subprocess=False in interactive mode
    driver = uc.Chrome(headless=False, use_subprocess=True)
    wait = WebDriverWait(driver, 5)

    LOGGER.info('downloading mortgage rates')
    mortgage_rate_30, mortgage_rate_20, mortgage_rate_15 = download_mortgage_rates(dirpath=args.output_dirpath)
    LOGGER.info('30 Year mortgage rate of %0.2f%%', mortgage_rate_30)

    if args.commute:
        realtor_com_populate_commute(driver, wait, urls[-1], args.commute)

    LOGGER.info('url processing')
    properties = []
    for u, url in enumerate(urls):
        LOGGER.info('%d / %d - %s', u + 1, len(urls), url)

        cached_filepath = abspath(args.output_dirpath, f'{u}.txt')
        if is_file(cached_filepath):
            text = read_text_file(cached_filepath)
        else:
            text = realtor_com_to_text(driver, wait, url.strip())
            write_text_file(cached_filepath, f'{url}\n{text}')

        prop = Property.parse_realtor_com(text)
        prop.link = url
        prop.calculate(mortgage_rate_15, mortgage_rate_20, mortgage_rate_30)
        properties.append(prop)

    property_dicts = [asdict(prop) for prop in properties]
    keys = list(asdict(DEFAULT_PROPERTY).keys())
    output_filepath_csv = abspath(args.output_dirpath, f'{filename}.csv')
    with open(output_filepath_csv, 'w', encoding='utf-8', newline='') as w:
        writer = csv.DictWriter(w, fieldnames=keys)
        writer.writeheader()
        writer.writerows(property_dicts)

    output_filepath_json = abspath(args.output_dirpath, f'{filename}.json')
    with open(output_filepath_json, 'w', encoding='utf-8') as w:
        json.dump(property_dicts, w, indent=2)

    LOGGER.info('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
