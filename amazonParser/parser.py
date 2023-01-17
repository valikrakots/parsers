from random import randint
from time import sleep

import pandas as pd
from pandas import DataFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager



def get_driver():
    options = Options()
    options.headless = False
    options.add_argument("--window-size=1920,1200")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def parse_doc():
    ex_data = pd.read_excel('Список асинов.xlsx')
    list = ex_data['ASIN'].tolist()
    return list


def parse(list):
    url = 'https://www.amazon.com/dp/'
    res = []
    first = True

    driver = get_driver()

    for l in list:
        prod_url = url + l

        try:
            driver.get(prod_url)
        except Exception as e:
            print(l + ': ' + str(e))
            res.append('Page not found')

        sleep(2)

        if first:
            first = False
            driver.find_element(By.ID, 'nav-global-location-popover-link').click()
            sleep(3)
            driver.find_element(By.ID, 'GLUXZipUpdateInput').send_keys('10009')
            sleep(2)
            driver.find_element(By.ID, 'GLUXZipUpdate').click()
            sleep(3)
            driver.find_element(By.XPATH, "//div[contains(@class,'a-popover-footer')]/span").click()
            #driver.find_element(By.CLASS_NAME, 'a-button-primary').click()
            #driver.find_element(By.XPATH("//span[@data-action='GLUXConfirmAction']")).click()a-button-inner a-declarative
            sleep(3)

        success = False

        try:
            #store = driver.find_element(By.ID, 'sellerProfileTriggerId').text
            store = driver.find_elements(By.XPATH, "//div[contains(@tabular-attribute-name,'Sold by')]/div/span")[
                1].text
            res.append(store)
            success = True
        except:
            try:
                #store = driver.find_elements(By.XPATH, "//div[contains(@tabular-attribute-name,'Sold by')]/div/span")[1].text
                store = driver.find_element(By.XPATH, "//div[contains(@id,'shipsFromSoldByMessage_feature_div')]/div"
                                                       "/span").text
                res.append(store)
                success = True
            except Exception as e2:
                print(l + ': ' + str(e2))
        finally:
            if not success:
                res.append('Error: unable to parse')
        sleep(randint(3, 6))


    df = DataFrame({'Stimulus Time': list, 'Reaction Time': res})
    df.to_excel('stores.xlsx', sheet_name='parsed', index=False)
    driver.quit()



l = parse_doc()
parse(l)


# def parse(list):
#     url = 'https://www.amazon.com/dp/'
#     res = []
#     for l in list:
#         prod_url = url + l
#         # prod_url = 'https://www.amazon.com/dp/B07PJLLSKK'
#         response = requests.get(prod_url, headers=HEADERS)
#         text = response.content
#         content = bs(text, 'lxml')
#         notFound = content.find("div", id='outOfStock')
#         print(content)
#         if notFound:
#             res.append('')
#         else:
#             name = content.find("div", class_ = "tabular-buybox-text a-spacing-none")
#             res.append(name.text)
#
#           HEADERS ={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0", "Accept-Encoding":"gzip, deflate", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT":"1","Connection":"close", "Upgrade-Insecure-Requests":"1", 'X-User-IP': '185.212.169.106'}
#
#         # res = content.find_all("div", class_= "tabular-buybox-text a-spacing-none")
#         # print(res)
#         # print('')
#
#     df = DataFrame({'Stimulus Time': list, 'Reaction Time':res })
#     df.to_excel('test.xlsx', sheet_name='sheet1', index=False)






