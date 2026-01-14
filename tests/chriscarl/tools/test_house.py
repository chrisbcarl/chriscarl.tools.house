#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-12
Description:

chriscarl.tools.house unit test.

Updates:
    2026-01-12 - tests.chriscarl.tools.house - initial commit
'''

# stdlib imports (expected to work)
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import unittest
import json

# third party imports
import undetected_chromedriver as uc
from selenium.webdriver.support.wait import WebDriverWait

# project imports (expected to work)
from chriscarl.core import constants
from chriscarl.core.lib.stdlib.os import abspath
from chriscarl.core.lib.stdlib.unittest import UnitTest
from chriscarl.core.lib.stdlib.io import read_text_file

# test imports
import chriscarl.tools.house as lib

SCRIPT_RELPATH = 'tests/chriscarl/tools/test_house.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

constants.fix_constants(lib)  # deal with namespace sharding the files across directories


class TestCase(UnitTest):

    def setUp(self):
        self.driver = uc.Chrome(headless=False, use_subprocess=True)
        self.wait = WebDriverWait(self.driver, 5)  # strictly absurd
        # $1,674,999 2/2 is absurd
        self.realtor_com_url = 'https://www.realtor.com/realestateandhomes-detail/7931-Caledonia-Dr_San-Jose_CA_95135_M19351-48449'
        self.zillow_com_url = 'https://www.zillow.com/homedetails/2151-Oakland-Rd-SPC-297-San-Jose-CA-95131/2096960515_zpid/'
        self.commute_address = '1 Washington Sq, San Jose, CA, 95112'
        self.realtor_com_text = read_text_file(abspath(constants.TEST_COLLATERAL_DIRPATH, 'realtor.com.txt'))
        self.zillow_com_text = read_text_file(abspath(constants.TEST_COLLATERAL_DIRPATH, 'zillow.com.txt'))
        return super().setUp()

    def tearDown(self):
        self.driver.quit()
        return super().tearDown()

    # @unittest.skip('lorem ipsum')
    def test_case_0_mortgage(self):
        tpl = lib.download_mortgage_rates()
        variables = [
            (lib.mortgage_monthly, (848000, 6.088)),
            (lib.mortgage_monthly, (848000, 0.06088)),
            (isinstance, (tpl, tuple)),
            (isinstance, (tpl[0], float)),
            (isinstance, (tpl[2], float)),
        ]
        controls = [
            4106,
            4106,
            True,
            True,
            True,
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_1_realtor_com_text_to_property(self):
        prop = lib.Property.parse_text(self.realtor_com_text, hostname='realtor.com')
        variables = [
            (getattr, (prop, 'address')),
            (getattr, (prop, 'property_type')),
            (getattr, (prop, 'price')),
            (getattr, (prop, 'bed')),
            (getattr, (prop, 'bath')),
            (getattr, (prop, 'area')),
            (getattr, (prop, 'commute')),
            (getattr, (prop, 'listing_age')),
            (getattr, (prop, 'listing_agent')),
        ]
        controls = [
            '1300 E San Antonio St Spc 67, San Jose, CA 95116',  # 'address'
            'Single family',  # 'property_type'
            139990,  # 'price'
            1,  # 'bed'
            1,  # 'bath'
            297,  # 'area'
            '7 min',  # 'commute'
            40,  # 'listing_age'
            'John A. Mcdougall III',  # 'listing_agent'
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_2_realtor_com_to_text(self):
        text = lib.realtor_com_to_text(self.driver, self.wait, self.realtor_com_url, sleep_for=0)
        prop = lib.Property.parse_text(text, hostname='realtor.com')
        variables = [
            (getattr, (prop, 'address')),
            (getattr, (prop, 'year')),
        ]
        controls = [
            '7931 Caledonia Dr, San Jose, CA 95135',
            1988,
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_3_realtor_com_populate_commute(self):
        variables = [
            (lib.realtor_com_populate_commute, (self.driver, self.wait, self.realtor_com_url, self.commute_address)),
        ]
        controls = [
            True,
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_4_zillow_com_text_to_property(self):
        prop = lib.Property.parse_text(self.zillow_com_text, hostname='zillow.com')
        LOGGER.info("%s", json.dumps(prop.to_dict(), indent=2))
        variables = [
            (getattr, (prop, 'address')),
            (getattr, (prop, 'property_type')),
            (getattr, (prop, 'price')),
            (getattr, (prop, 'bed')),
            (getattr, (prop, 'bath')),
            (getattr, (prop, 'area')),
            # (getattr, (prop, 'commute')),
            (getattr, (prop, 'listing_age')),
            (getattr, (prop, 'listing_agent')),
        ]
        controls = [
            '516 Martha St UNIT 101, San Jose, CA 95112',  # 'address'
            'Condo',  # 'property_type'
            380000,  # 'price'
            1,  # 'bed'
            1,  # 'bath'
            368,  # 'area'
            # '7 min',  # 'commute'
            3,  # 'listing_age'
            'Terese Ferrara',  # 'listing_agent'
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_5_zillow_com_to_text(self):
        text = lib.zillow_com_to_text(self.driver, self.wait, self.zillow_com_url, sleep_for=0)
        prop = lib.Property.parse_text(text, hostname='zillow.com')
        LOGGER.info("%s", json.dumps(prop.to_dict(), indent=2))
        variables = [
            (getattr, (prop, 'address')),
            (getattr, (prop, 'year')),
        ]
        controls = [
            '2151 Oakland Rd SPC 297, San Jose, CA 95131',
            1978,
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_6_search(self):
        urls = lib.realtor_com_search(
            self.driver,
            self.wait,
            city='San Jose',
            state='CA',
            price_max=300000,  # NOTE: this could be genuinely too low depending on location
        )
        LOGGER.info("%s", json.dumps(urls, indent=2))
        self.assertTrue(urls)


if __name__ == '__main__':
    tc = TestCase()
    tc.setUp()

    tc.test_case_0_mortgage()
    tc.test_case_1_realtor_com_text_to_property()
    tc.test_case_2_realtor_com_to_text()
    tc.test_case_3_realtor_com_populate_commute()
    tc.test_case_4_zillow_com_text_to_property()
    tc.test_case_5_zillow_com_to_text()
    tc.test_case_6_search()

    tc.tearDown()
