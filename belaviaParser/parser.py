import datetime
import json
import os
import sys
from time import sleep

from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def add_day(day):
    day += datetime.timedelta(days=1)
    return day


def get_url(home, to, date):
    url = 'https://ibe.belavia.by/select?journey=' + home + to + date.strftime(
        '%Y%m%d') + '&adults=1&children=0&infants=0'
    return url


def printj(text):
    print(json.dumps(text))


def generate_options():
    options = Options()
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--no-sandbox")
    # options.add_argument("--headless=True")
    options.add_argument('--disable-blink-features=AutomationControlled')
    data_dir = ROOT_DIR + '\\profiles\\selenium_prof'
    options.add_argument(f"--user-data-dir={data_dir}")
    options.add_argument('--profile-directory=Default')
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f"--user-agent={user_agent}")
    return options


def get_driver(url):
    for _ in range(3):
        options = generate_options()
        quit = True
        driver = uc.Chrome(options=options)
        try:
            driver.get(url)
            overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'overlay')]")
            i = 0
            skip = False
            while overlay:
                if i > 25:
                    skip = True
                    break
                sleep(1)
                i += 1
                overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'overlay')]")
            if not skip:
                ok_but = driver.find_elements(By.XPATH, "//button[contains(@type,'button')]")
                if len(ok_but) == 4:
                    printj({'err': 'модальное окно'})
                    return None
                captcha = driver.find_elements(By.XPATH, "//div[contains(@id,'g-recaptcha')]")
                if len(captcha) == 0:
                    quit = False
                    return driver
            printj({"err": "captcha appeared"})
            sleep(1)
        except:
            printj({"err": "error while opening browser"})
        finally:
            if quit:
                driver.quit()
    return None


def parse(home, to, date_home, date_to):
    url = 'https://ibe.belavia.by/select?journey=' + home + to + date_home + '&adults=1&children=0&infants=0'
    driver = get_driver(url)
    day_date = datetime.datetime.strptime(date_home, "%Y%m%d").date()
    date_to = add_day(datetime.datetime.strptime(date_to, "%Y%m%d").date())

    if driver is None:
        printj({'Error': 'Unable to parse'})
        return

    try:
        sleep(5)
        res = {}
        day_els = driver.find_elements(By.XPATH, "//div[contains(@class,'day')]")
        skip = True
        for day in day_els:
            date = day.find_element(By.CLASS_NAME, 'date')
            if skip and date.text.find(date_home[-2:]) != -1:
                skip = False
            elif skip:
                continue
            elif date_to == day_date:
                # json_res = json.dumps(res)
                printj(res)
                driver.quit()
                return

            price_val = ''
            try:
                price = day.find_element(By.CLASS_NAME, 'price-value')
                price_val = price.text
            except:
                pass

            url = get_url(home, to, day_date)
            values_dict = {
                'url': url,
                'price': price_val,
            }
            res[day_date.strftime('%d %B %Y')] = values_dict
            day_date = add_day(day_date)

        while True:
            driver.find_element(By.XPATH, "//button[contains(@class,'nav-right')]").click()
            sleep(3)
            day_els = driver.find_elements(By.XPATH, "//div[contains(@class,'day')]")
            for day in day_els:
                date = day.find_element(By.CLASS_NAME, 'date')
                if date_to == day_date or day_date > date_to:
                    printj(res)
                    driver.quit()
                    return

                price_val = ''
                try:
                    price = day.find_element(By.CLASS_NAME, 'price-value')
                    price_val = price.text
                except:
                    pass

                url = get_url(home, to, day_date)
                values_dict = {
                    'url': url,
                    'price': price_val,
                }
                res[day_date.strftime('%d %B %Y')] = values_dict
                day_date = add_day(day_date)

    except Exception as e:
        printj({'err': 'Error while parsing'})


if __name__ == "__main__":
    # parse(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    parse('MSQ', 'DXB', '20221129', '20221130')
