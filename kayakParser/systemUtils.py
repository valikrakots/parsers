import datetime

import pytz
import requests


def localToUtc(localDt):
    return localDt.astimezone(pytz.utc)


def utcToLocal(utcDt):
    return utcDt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)


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

    for t in text[::7]:
        resultStr = t.get_attribute('outerText')
        res = resultStr.split('\n')
        for i in range(len(res)):
            if (' am–' in res[i]) or (' pm–' in res[i]):
                res = res[i:]
                break
        if '+' in res[0]:
            resStr = res[0]
            res[0] = resStr[:resStr.find('+')]
        depArv = res[0].split('–')
        departures.append(depArv[0].split(' ')[0])
        arrivals.append(depArv[1].split(' ')[0])
        timeMeridians.append(depArv[0].split(' ')[1])
        timeMeridians.append(depArv[1].split(' ')[1])

    departures, arrivals = getTime(departures, arrivals, timeMeridians)
    return departures, arrivals


def checkDate(dateFrom, flight, kayakDb):
    if dateFrom.date() < datetime.datetime.now().date():
        while dateFrom.date() < datetime.datetime.now().date():
            dateFrom += datetime.timedelta(days=1)
        kayakDb.flightsUpdateDate(flight, dateFrom)
    return dateFrom


def userSendParsed(kayakDb, flightId):
    flight = kayakDb.flightsGet(flightId)
    if kayakDb.usersGetNotify(flight.get('user')):
        chatId = kayakDb.usersGetChatId(flight.get('user'))
        if chatId is not None:
            text = f"На ваш рейс {flight.get('direction').get('from')} - {flight.get('direction').get('to')}" \
                   f" ({utcToLocal(flight.get('date').get('from')).date()} - {utcToLocal(flight.get('date').get('to')).date()}) " \
                   f"все данные получены"
            url = f"https://api.telegram.org/bot5721815974:AAHNiAflHIuJIorWTpdYMj6YHdhz7_BLx24/sendMessage?chat_id={chatId}" \
                  f"&text={text}"
            requests.get(url)


def usersSendUnavailable(kayakDb, users, ticket):
    for user in users:
        if kayakDb.usersGetNotify(user):
            chatId = kayakDb.usersGetChatId(user)
            if chatId is not None:
                text = f"Ваш рейс {ticket.fromCity} - {ticket.toCity} недоступен " \
                       f"к парсингу из-за ограничения регионов в kayak"
                url = f"https://api.telegram.org/bot5721815974:AAHNiAflHIuJIorWTpdYMj6YHdhz7_BLx24/sendMessage?" \
                      f"chat_id={chatId}&text={text}"
                requests.get(url)

