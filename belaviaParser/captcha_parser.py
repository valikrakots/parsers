import urllib
from time import sleep
from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from urllib.request import urlretrieve


def generate_options():
    options = Options()
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--no-sandbox")
    #options.add_argument("--headless=False")
    options.add_argument('--disable-blink-features=AutomationControlled')
    return options


def get_driver(url):
    options = generate_options()
    driver = uc.Chrome(options=options, use_subprocess=True)
    try:
        i = 1
        while i < 100:
            driver.get(url)
            overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'overlay')]")
            while overlay:
                sleep(1)
                overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'overlay')]")

                # ok_but = driver.find_elements(By.XPATH, "//button[contains(@type,'button')]")
                # if len(ok_but) == 4:
                #     printj({'err': 'модальное окно'})
                #     return None
            captcha = driver.find_elements(By.XPATH, "//div[contains(@id,'g-recaptcha')]")
            print(f'Step {i}')
            if len(captcha) != 0:
                print('Captcha found')
                img = driver.find_element(By.XPATH, '//div[contains(@class,"form-group")]/img')
                src = img.get_attribute('src')
                # download the image
                urlretrieve(src, f"captchas\\{i+1}.png")

            i += 1
            sleep(5)
    except Exception as e:
        print('Error with driver')
        print(e)
    finally:
        driver.quit()


if __name__ == '__main__':
    url = 'https://ibe.belavia.by/select?journey=MSQDXB20221212&adults=1&children=0&infants=0'
    get_driver(url)

