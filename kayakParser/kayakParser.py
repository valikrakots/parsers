import datetime
import logging
import random
from threading import current_thread
from time import sleep


from kayakDB import KayakDatabase
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

from systemUtils import getTime, parseResStr, usersSendUnavailable


def getDriver(threadName):
    options = uc.ChromeOptions()
    options.user_data_dir = f".\\cache\\{str(threadName)}"
    options.headless = True
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def getHeadDriver(flightId):
    options = uc.ChromeOptions()
    options.user_data_dir = f".\\cache\\{str(flightId)}"
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def solveCaptcha(driver):
    sleep(3)
    try:
        iframe= driver.find_element(By.XPATH, "//iframe[@title, 'reCAPTCHA']")
        driver.switch_to.frame(iframe)
        captcha = driver.find_element(By.XPATH, "//span[contains(@id, 'recaptcha-anchor')]")
        captcha.click()
        print('Recaptcha appeared and was clicked')
        sleep(4)
    except:
        pass
    try:
        iframe = driver.find_element(By.XPATH,
                                     "//iframe[contains(@title, 'Widget containing a Cloudflare security challenge')]")
        driver.switch_to.frame(iframe)
        but = driver.find_element(By.XPATH, "//span[contains(@class, 'mark')]")
        but.click()
        print('Cloudcaptcha appeared and was clicked')
        sleep(4)
    except:
        pass
    try:
        iframes = driver.find_elements(By.XPATH, "//iframe")
        print(f"Found {len(iframes)} iframes")
        driver.switch_to.frame(iframes[0])
        captcha = driver.find_element(By.XPATH, "//span[contains(@id, 'recaptcha-anchor')]")
        captcha.click()
        print('Recaptcha appeared and was clicked')
        sleep(4)
    except:
        pass


def waitLoad(driver):
    slept = 0
    text = driver.find_element(By.XPATH, "//div[contains(@class,'col-advice')]/div").text
    while 'Loading' in text:
        sleep(1)
        text = driver.find_element(By.XPATH, "//div[contains(@class,'col-advice')]/div").text
        slept += 1
        if slept % 10 == 0:
            try:
                driver.find_element(By.XPATH, "//div[contains(@class, 'resultsList hidden')]")
                return False
            except:
                pass
        if slept % 30 == 0:
            print(f'Waitload sleeping for {slept} trying to move mouse')
    return True


def getTicketsSecond(driver):
    text = driver.find_elements(By.XPATH, "//div[contains(@class, 'nrc6')]")  # .get_attribute('outerText')
    departures, arrivals = parseResStr(text)

    durations = [dur.text for dur in driver.find_elements(By.XPATH, "//div[contains(@class, 'xdW8')]/div")
                 if '-' not in dur.text]
    prices = [int(price.text[1:].replace(',', '')) for price in
              driver.find_elements(By.XPATH, "//div[contains(@class, 'f8F1-price-text')]")]
    links = [lnk.get_attribute('href') for lnk in
             driver.find_elements(By.XPATH, "//a[contains(@class, 'Button-No-Standard-Style')]")]
    return departures, arrivals, durations, prices, links


def getTickets(driver):
    stops = [stp.text.replace(' stops', '') for stp in
             driver.find_elements(By.XPATH, "//span[contains(@class, 'stops-text')]")]
    stops = [0 if stop == 'nonstop' else int(stop[:1]) for stop in stops]
    departures = [dep.text for dep in driver.find_elements(By.XPATH, "//span[contains(@class, 'depart-time')]")]

    if len(stops) != len(departures):
        departures, arrivals, durations, prices, links = getTicketsSecond(driver)
        return stops, departures, arrivals, durations, prices, links

    arrivals = [arv.text for arv in driver.find_elements(By.XPATH, "//span[contains(@class, 'arrival-time')]")]
    timeMeridians = [mer.text for mer in driver.find_elements(By.XPATH, "//span[contains(@class, 'time-meridiem')]")]
    departures, arrivals = getTime(departures, arrivals, timeMeridians)

    durations = [dur.text for dur in driver.find_elements(By.XPATH, "//div[contains(@class, 'duration')]/div[contains"
                                                                    "(@class, 'top')]")]
    prices = [int(prc.text[1:].replace(',', '')) for prc in
              driver.find_elements(By.XPATH, "//span[contains(@class, 'price-text')]") if
              prc.text != '']
    links = [lnk.get_attribute('href') for lnk in
             driver.find_elements(By.XPATH, "//a[contains(@class, 'booking-link')]") if
             ('View Deal' not in lnk.text and '$' not in lnk.text and lnk.text != '')]
    return stops, departures, arrivals, durations, prices, links


def checkCountry(driver):
    try:
        noRes = driver.find_element(By.XPATH, "//ul[contains(@class, 'errorMessages')]/li")
        return True if noRes is not None else False
    except Exception as e:
        return False


def getUrl(driver, url):
    sleep(1)
    driver.get(url)
    sleep(4)


def getInfo(ticketsToParse, runningThreads, kayakDb, driver):
    threadName = current_thread().name

    while True:
        if not runningThreads.get(threadName):
            logging.warning(f'Thread {threadName} was finished due to not many tickets: {len(ticketsToParse)}')
            return

        while len(ticketsToParse) == 0:
            sleep(2)

        ticket = ticketsToParse.pop(0)

        fromCity = ticket.fromCity
        toCity = ticket.toCity
        dateToParse = ticket.departureDate
        url = ticket.url

        try:

            if dateToParse.date() < datetime.datetime.now().date():
                ticket.deleteTicketFromDb(kayakDb.ticketsDb)
                continue

            getUrl(driver, url)

            if checkCountry(driver):
                users = kayakDb.flightsSetUnavailable(ticket)
                usersSendUnavailable(kayakDb, users, ticket)
                for t in ticketsToParse:
                    if t.fromCity == ticket.fromCity and t.toCity == toCity:
                        ticketsToParse.remove(t)
                logging.warning(f'Kayak not displaying for {fromCity} or {toCity}')
                continue

            try:
                available = waitLoad(driver)
            except:
                solveCaptcha(driver)
                try:
                    available = waitLoad(driver)
                except:
                    raise Exception('Unable to solve captcha')

            if not available:
                kayakDb.ticketsWrite(ticket)
                logging.warning(f"No tickets {fromCity} - {toCity} on {dateToParse}\n")
                # print(f"No tickets {fromCity} - {toCity} on {dateToParse} or waitLoad error\n")
                continue

            stops, departures, arrivals, durations, prices, links = getTickets(driver)
            ticket.stops = stops
            ticket.departures = departures
            ticket.arrivals = arrivals
            ticket.durations = durations
            ticket.prices = prices
            ticket.links = links
            ticket.minPrice = min(prices) if (prices is not None and len(prices) > 0) else 0
            kayakDb.ticketsWrite(ticket)

        except Exception as e:
            logging.error(f"Unable to parse {fromCity} - {toCity} on {dateToParse}\nReason: {e}")
            print(f"Unable to parse {fromCity} - {toCity} on {dateToParse}\nReason: {e}")
            driver.save_screenshot(f"errorScreens/{threadName}_{datetime.datetime.now()}.png")
            ticket.updateVersion(kayakDb.ticketsDb)
            driver = getHeadDriver(threadName)
            getUrl(driver, url)
            #solveCaptcha(driver)
            sleep(6000)

        sleep(random.randint(4, 10))


def runParsing(ticketsToParse, runningThreads, db):
    threadName = current_thread().name
    driver = getDriver(threadName)
    kayakDb = KayakDatabase(db)

    try:
        getInfo(ticketsToParse, runningThreads, kayakDb, driver)
    except Exception as e:
        logging.error(f'There was an error in thread {threadName}\nReason: {e}')
        print(f'There was an error in thread {threadName}\nReason: {e}')
    finally:
        driver.close()
