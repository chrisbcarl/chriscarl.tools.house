# chriscarl.tools.house
In the search for a house, it would be nice to have an open browser and simply browse at leisure for listings rather than writing all that crap down.

# Usage
```bash
poetry install

house url-file files/house-links-2026-01.txt --commute "1 Washington Sq, San Jose, CA, 95112"

house browse --commute "1 Washington Sq, San Jose, CA, 95112"
```


# The Search
mobile home parks
https://www.mhbo.com/mobile-home-park/49916-san-jose-mobile-home-rv-park-1300-east-san-antonio-street-san-jose-ca-95116


mobile home order
https://factorybuilthomesdirect.com/



rent rooms
https://www.facebook.com/marketplace/item/1416298276657287/?ref=category_feed&referral_code=undefined&referral_story_type=listing&tracking=%7B%22qid%22%3A%22-7665026024942857965%22%2C%22mf_story_key%22%3A%2225892970153629190%22%2C%22commerce_rank_obj%22%3A%22%7B%5C%22target_id%5C%22%3A25892970153629190%2C%5C%22target_type%5C%22%3A0%2C%5C%22primary_position%5C%22%3A31%2C%5C%22ranking_signature%5C%22%3A6067870476988819790%2C%5C%22ranking_request_id%5C%22%3A604190408405241506%2C%5C%22commerce_channel%5C%22%3A504%2C%5C%22value%5C%22%3A0.00039562581862357%2C%5C%22candidate_retrieval_source_map%5C%22%3A%7B%5C%2225892970153629190%5C%22%3A204%7D%7D%22%7D


mortgage calculator
https://www.realtor.com/mortgage/tools/mortgage-calculator/?msockid=0bc138a3860966de16bb2e69877f67b7


all about land leases and having the text of the lease
https://www.pew.org/en/research-and-analysis/articles/2025/06/04/millions-of-homeowners-who-rent-land-are-at-risk-of-price-increases-or-eviction



# Features
|version    |author     |deployed   |created    |feature-name                           |description        |
|---        | ---       | ---       | ---       | ---                                   | ---               |


# Acknowledgements
- [Forbes](https://www.forbes.com/advisor/mortgages/current-20-year-mortgages-rates/) for collating the mortgage rates and updating them daily
- [Realtor.com Mortgage Calculator](https://www.realtor.com/mortgage/tools/mortgage-calculator) to verify values
- other possible links
    - https://www.scrapingbee.com/blog/web-scraping-realtor/
    - https://webscrapingsite.com/blog/how-to-scrape-data-from-realtor-com-a-comprehensive-guide/
    - https://webscraping.ai/faq/selenium-webdriver/how-do-i-manage-browser-profiles-and-preferences-in-selenium-webdriver
    - consider attaching to an existing session
        - https://stackoverflow.com/questions/8344776/can-selenium-interact-with-an-existing-browser-session
        - header interception - https://www.zenrows.com/blog/selenium-headers#set-up-custom-headers


# Dead Code
```python
    # options = webdriver.EdgeOptions()
    # # options.use_chromium = True
    # # options.add_argument("disable-features=LockProfileCookieDatabase")

    # EDGE_USER_DATA = abspath('~/AppData/Local/Microsoft/Edge/User Data')

    # options.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    # # options.add_argument(f'--user-data-dir={EDGE_USER_DATA}')
    # options.add_argument('--profile-directory=Default')
    # settings = {}
    # prefs = {}

    # # options.add_experimental_option('prefs', prefs)
    # # options.add_argument('--kiosk-printing')
    # driver = webdriver.Edge(options=options)
```