import logging
from time import sleep

from pymongo import MongoClient
import threading
from kayakDB import KayakDatabase
from kayakParser import runParsing
from systemUtils import userSendParsed


def runThread(allThreads, ticketsToParse, runningThreads, db):
    threadName = str(len(allThreads) + 1)
    t = threading.Thread(target=runParsing, name=threadName,
                         args=(ticketsToParse, runningThreads, db), daemon=True)
    allThreads.append(t)
    runningThreads[threadName] = True
    logging.warning(f'Thread {threadName} was added, current thread num: {len(allThreads)}')
    t.start()


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        filename='app.log',
                        level=logging.WARNING)
    client = MongoClient("mongodb+srv://asdqwe:asdqwe123@cluster0.aroxlrn.mongodb.net/db")
    db = client.valiantsindatabase
    kayakDb = KayakDatabase(db)

    allThreads = []
    ticketsToParse = []
    runningThreads = {'MainThread': True}
    parsedFlightsIds = []
    firstParsedFlights = {}

    runThread(allThreads, ticketsToParse, runningThreads, db)

    while True:
        if len(ticketsToParse) > 15:
            runThread(allThreads, ticketsToParse, runningThreads, db)

        newTickets, newFLights = kayakDb.flightsCreateAllUnparsedTickets()
        oldTickets = kayakDb.ticketsCheckOld()

        for ticket in newTickets:
            ticketsToParse.append(ticket)

        for flightId in newFLights:
            parsedFlightsIds.append(flightId)
            firstParsedFlights[flightId] = kayakDb.flightsGetDuration(flightId) + 1

        for ticket in oldTickets:
            ticketsToParse.append(ticket)

        for flightId in parsedFlightsIds:
            if not kayakDb.flightsCheckExists(flightId):
                kayakDb.flightsDeleteTickets(flightId)
                parsedFlightsIds.remove(flightId)

        print(len(ticketsToParse))
        if len(ticketsToParse) < 10:
            if len(allThreads) > 1:
                number = len(allThreads)
                runningThreads[str(number)] = False
                allThreads.pop()
                logging.warning(f'Thread {number} was deleted, current thread num: {len(allThreads)}')

        # print(firstParsedFlights)
        for flightId in list(firstParsedFlights):
            if flightId not in parsedFlightsIds:
                firstParsedFlights.pop(flightId)
                continue
            size = kayakDb.ticketsGetAllParsedForFlight(flightId)
            # print(f"{flightId} {size}")
            if firstParsedFlights.get(flightId) == size:
                userSendParsed(kayakDb, flightId)
                firstParsedFlights.pop(flightId)

        # getInfo(ticketsToParse, runningThreads, db)

        sleep(70)


if __name__ == '__main__':
    main()
