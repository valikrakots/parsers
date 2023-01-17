import datetime
from time import sleep
from kayakDB import Ticket, writeTicket, updateFlightDate
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc


def getDriver(flightId):
    options = uc.ChromeOptions()
    options.user_data_dir = f".\\cache\\{str(flightId)}"
    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def utcToLocal(utcDt):
    return utcDt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)


def waitLoad(driver):
    slept = 0
    text = driver.find_element(By.XPATH, "//div[contains(@class,'col-advice')]/div").text
    while 'Loading' in text:
        text = driver.find_element(By.XPATH, "//div[contains(@class,'col-advice')]/div").text
        sleep(1)
        slept += 1
        if slept == 15:
            try:
                driver.find_element(By.XPATH, "//div[contains(@class, 'resultsList hidden')]")
                return False
            except Exception as e:
                pass
    return True


def getTime(departures, arrivals, meridians):
    departureArr = []
    arrivalArr = []
    for i in range(len(departures)):
        departures[i] += ' ' + meridians[2 * i]
        formatTime = '%I:%M %p'
        departureTime = datetime.datetime.strptime(departures[i], formatTime).strftime("%H:%M")
        departureArr.append(departureTime)

        arrivals[i] += ' ' + meridians[2 * i + 1]
        arrivalTime = datetime.datetime.strptime(arrivals[i], formatTime).strftime("%H:%M")
        arrivalArr.append(arrivalTime)

    return departureArr, arrivalArr


def parseResStr(text):
    departures = []
    arrivals = []
    timeMeridians = []
    durations = []
    prices = []

    for t in text[::7]:
        resultStr = t.get_attribute('outerText')
        res = resultStr.split('\n')
        depArv = res[0][:-2].split('–')
        departures.append(depArv[0].split(' ')[0])
        arrivals.append(depArv[1].split(' ')[0])
        timeMeridians.append(depArv[0].split(' ')[1])
        timeMeridians.append(depArv[1].split(' ')[1])
        durations.append(res[4])
        prices.append(int(res[11][1:].replace(',', '')))

    return departures, arrivals, timeMeridians, durations, prices


def getTicketsSecond(driver):
    text = driver.find_elements(By.XPATH, "//div[contains(@class, 'nrc6')]")  # .get_attribute('outerText')
    departures, arrivals, timeMeridians, durations, prices = parseResStr(text)
    departures, arrivals = getTime(departures, arrivals, timeMeridians)

    links = [lnk.get_attribute('href') for lnk in
             driver.find_elements(By.XPATH, "//a[contains(@class, 'Button-No-Standard-Style')]")]
    return departures, arrivals, durations, prices, links


def getTickets(driver):
    stops = [stp.text.replace(' stops', '') for stp in
             driver.find_elements(By.XPATH, "//span[contains(@class, 'stops-text')]")]
    stops = [0 if stop == 'nonstop' else int(stop) for stop in stops]
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


def checkCountry(driver, url):
    try:
        driver.get(url)
        noRes = driver.find_element(By.XPATH, "//ul[contains(@class, 'errorMessages')]/li")
        return True if noRes is not None else False
    except Exception as e:
        return False


def getInfo(flight, db):
    fromCity = flight.get('direction').get('from')
    toCity = flight.get('direction').get('to')
    fromIATA = flight.get('direction').get('fromCode')
    toIATA = flight.get('direction').get('toCode')
    dateFrom = utcToLocal(flight.get('date').get('from'))
    dateTo = utcToLocal(flight.get('date').get('to'))

    driver = getDriver(flight.get('_id'))
    try:

        url = f'https://www.kayak.com/flights/{fromIATA}-{toIATA}/{dateFrom.strftime("%Y-%m-%d")}?sort=price_a'
        if checkCountry(driver, url):
            sleep(2)
            raise Exception(f'Kayak not displaying for {fromCity} or {toCity}')
        while True:

            if dateFrom < datetime.datetime.now():
                newDate = datetime.datetime.combine(datetime.datetime.now().date(), datetime.time(0, 0, 0))
                updateFlightDate(flight.get('_id'), newDate, db)

            while dateFrom <= dateTo:
                sleep(4)
                driver.get(url)
                sleep(1)

                available = waitLoad(driver)
                if not available:
                    ticket = Ticket(fromCity, toCity, dateFrom, url)
                    writeTicket(ticket, db)
                    continue

                stops, departures, arrivals, durations, prices, links = getTickets(driver)
                ticket = Ticket(fromCity, toCity, dateFrom, url, departures, arrivals, stops, durations, prices, links)
                writeTicket(ticket, db)
                dateFrom = dateFrom + datetime.timedelta(days=1)
                url = f'https://www.kayak.com/flights/{fromIATA}-{toIATA}/{dateFrom.strftime("%Y-%m-%d")}?sort=price_a'
            sleep(300)
    except Exception as e:
        print(f"Unable to parse {fromIATA} - {toIATA} on {dateFrom}\nReason: {e}")
    finally:
        driver.close()
